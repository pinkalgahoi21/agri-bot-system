from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
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
    user_id: int
    message: str

@router.post("/chat")
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    farmer = db.query(models.Farmer).filter(models.Farmer.user_id == request.user_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found. Please complete your profile.")
    
    state = {
        "user_id": farmer.user_id,
        "name": farmer.name,
        "location": farmer.location,
        "crop": farmer.crop,
        "messages": [HumanMessage(content=request.message)]
    }

    config = {"configurable": {"thread_id": str(request.user_id)}}
    result = graph_app.invoke(state, config=config)
    final_message = result["messages"][-1].content
    
    return {"response": final_message}

@router.post("/profile")
def create_profile(user_id: int = Form(...), name: str = Form(...), city: str = Form(...), location: str = Form(...), crop: str = Form(...), db: Session = Depends(get_db)):
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
def vision(user_id: int = Form(...), image: UploadFile = File(...), db: Session = Depends(get_db)):
    farmer = db.query(models.Farmer).filter(models.Farmer.user_id == user_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="Farmer not found. Please complete your profile.")

    # Save uploaded file to temp
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
    try:
        shutil.copyfileobj(image.file, tmp)
        tmp.close()
        
        profile_dict = {"location": farmer.location, "crop": farmer.crop, "name": farmer.name}
        result = analyze_crop_image(tmp.name, profile_dict)
        if not result:
            raise HTTPException(status_code=500, detail="Image analysis failed.")
            
        return {"response": result}
    finally:
        if os.path.exists(tmp.name):
            os.remove(tmp.name)

@router.post("/voice")
def voice(user_id: int = Form(...), audio: UploadFile = File(...), db: Session = Depends(get_db)):
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
            
        # Run through chat agent
        state = {
            "user_id": farmer.user_id,
            "name": farmer.name,
            "location": farmer.location,
            "crop": farmer.crop,
            "messages": [HumanMessage(content=text)]
        }
        config = {"configurable": {"thread_id": str(user_id)}}
        result = graph_app.invoke(state, config=config)
        final_message = result["messages"][-1].content
        
        # TTS
        tts_path = text_to_speech(final_message, lang)
        if not tts_path:
            return {"response": final_message, "transcribed": text} # fallback to text
            
        return FileResponse(tts_path, media_type="audio/mpeg", filename="response.mp3")
        
    finally:
        cleanup_file(tmp_in.name)
        cleanup_file(wav_path)
        # Note: tts_path is returned by FileResponse, so FastAPI handles cleanup or we might leak it. 
        # But for this demo, it's fine.
