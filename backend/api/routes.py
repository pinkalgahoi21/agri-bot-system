from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
import base64
import logging
from pathlib import Path
from pydantic import BaseModel
from sqlalchemy.orm import Session
from api.auth import identity
from services.advisory import offline_answer, parse_answer
from services.treatment_flow import assess
from services.farm_memory import recall, remember
import json
from services.language_service import normalize_language
import shutil
import os
import tempfile

from database.database import get_db
from database import models
from graph.agent import app as graph_app
from langchain_core.messages import HumanMessage

from services.image_service import analyze_crop_image
from services.voice_service import convert_ogg_to_wav, transcribe_voice, text_to_speech, cleanup_file

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@router.post("/chat")
def chat(request: ChatRequest, user_id: int = Depends(identity), db: Session = Depends(get_db)):
    farmer = db.query(models.Farmer).filter(models.Farmer.user_id == user_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found. Please complete your profile.")
    
    return advise(db, farmer, request.message)


def advise(db, farmer, message):
    previous, revision = recall(db, farmer)
    contextual = json.dumps({"prior_farm_note": previous, "current_request": message}, ensure_ascii=False) if previous else message
    state = {
        "user_id": farmer.user_id,
        "name": farmer.name,
        "location": farmer.location,
        "crop": farmer.crop,
        "messages": [HumanMessage(content=contextual)]
    }
    try:
        assessment = assess(contextual, farmer.crop)
        if assessment is None:
            result = graph_app.invoke(state, config={'recursion_limit': 8})
            assessment = parse_answer(result['messages'][-1].content)
        if not assessment.get("out_of_scope"):
            remember(db, farmer, previous, revision, message, assessment["response"])
        return assessment
    except Exception:
        logging.getLogger(__name__).warning('Advisory unavailable', exc_info=True)
        return offline_answer(message, farmer.crop, farmer.location)


@router.post("/profile")
def create_profile(user_id: int = Depends(identity), name: str = Form(...), city: str = Form(...), location: str = Form(...), crop: str = Form(...), db: Session = Depends(get_db)):
    farmer = db.query(models.Farmer).filter(models.Farmer.user_id == user_id).first()
    if farmer:
        farmer.name = name
        farmer.city = city
        farmer.location = location
        farmer.crop = crop
    else:
        farmer = models.Farmer(user_id=user_id, name=name, city=city, location=location, crop=crop)
        db.add(farmer)
    
    db.commit()
    return {"status": "success"}

@router.post("/vision")
def vision(user_id: int = Depends(identity), image: UploadFile = File(...), language: str = Form("en"), caption: str = Form("", max_length=1024), db: Session = Depends(get_db)):
    import logging
    logger = logging.getLogger(__name__)
    
    farmer = db.query(models.Farmer).filter(models.Farmer.user_id == user_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found. Please complete your profile.")

    # Save uploaded file to temp
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    try:
        shutil.copyfileobj(image.file, tmp)
        tmp.close()
        
        file_size = os.path.getsize(tmp.name)
        logger.info(f"Vision: received image ({file_size} bytes) from user {user_id}")
        
        if file_size == 0:
            raise HTTPException(status_code=400, detail="Uploaded image is empty.")
        
        profile_dict = {"location": farmer.location, "crop": farmer.crop, "name": farmer.name, "language": normalize_language(language)}
        profile_dict["caption"] = caption
        result = analyze_crop_image(tmp.name, profile_dict)
        if not result:
            logger.error(f"Vision: analyze_crop_image returned None for user {user_id}")
            return {'fallback': True, 'response': {'identified_crop': 'Unknown', 'disease': 'Not assessed', 'confidence': 'Low', 'severity': 'Unknown', 'cause': 'Image analysis unavailable.', 'prevention': ['Retry with a clear photo or describe the symptoms by text.'], 'urgency': 'Not assessed'}}
            
        match = result.get("crop_match", "uncertain")
        if match != "match" or result.get("identified_crop") in ("unknown", "not_a_plant"):
            notice = result.get("crop_notice") or "I could not confirm the expected crop. Please send a clearer photo."
            return {"response": {"kind": "crop_notice", "message": notice}}
        if result.get("confidence", "Low").lower() == "low" or result.get("disease", "").lower().startswith(("unclear", "unknown")):
            return {"response": {"kind": "crop_notice", "message": "I cannot identify the issue confidently. Please send a clearer photo of the affected area."}}
        try:
            previous, revision = recall(db, farmer)
            assessment = assess({**result, "prior_farm_note": previous, "reply_language": profile_dict["language"]}, result["identified_crop"], image=True)
            result["treatment"] = assessment["response"]
            remember(db, farmer, previous, revision, {"caption": caption, "photo_findings": result["disease"]}, assessment["response"])
        except Exception:
            logger.warning("Photo treatment lookup unavailable", exc_info=True)
            result["treatment"] = "Treatment assessment unavailable. No treatment was verified."
        return {"response": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vision: unexpected error for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Image analysis failed. Please try again.")
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)

@router.post("/voice")
def voice(user_id: int = Depends(identity), audio: UploadFile = File(...), db: Session = Depends(get_db)):
    farmer = db.query(models.Farmer).filter(models.Farmer.user_id == user_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found. Please complete your profile.")
        
    tmp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
    wav_path = None
    tts_path = None
    try:
        shutil.copyfileobj(audio.file, tmp_in)
        tmp_in.close()
        
        wav_path = convert_ogg_to_wav(tmp_in.name)
        if not wav_path:
            raise HTTPException(status_code=500, detail="Failed to convert audio.")
            
        text, lang = transcribe_voice(wav_path)
        if not text:
            raise HTTPException(status_code=400, detail="Could not understand audio.")
            
        reply = advise(db, farmer, text)
        reply['transcribed'] = text
        try:
            tts_path = text_to_speech(reply['response'], lang)
            if tts_path:
                reply['audio_base64'] = base64.b64encode(Path(tts_path).read_bytes()).decode('ascii')
        except Exception:
            logging.getLogger(__name__).warning('Speech synthesis unavailable')
        return reply
        
    finally:
        cleanup_file(tmp_in.name)
        cleanup_file(wav_path)
        cleanup_file(tts_path)
