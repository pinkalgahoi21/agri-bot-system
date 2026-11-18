import io
import json
import unittest
from unittest.mock import Mock, patch

from fastapi import UploadFile
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from database.database import Base
from database.models import Farmer
from services.farm_memory import recall, remember
from api.routes import voice


class ContinuityTests(unittest.TestCase):
    def test_memory_is_bounded_and_crop_scoped(self):
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        with Session(engine) as db:
            farmer = Farmer(user_id=1, crop="Rice")
            db.add(farmer)
            db.commit()
            with patch("services.farm_memory._chat", return_value=json.dumps({"summary": "x" * 900})):
                remember(db, farmer, "", 0, "test", "test")
            self.assertEqual(recall(db, farmer), ("x" * 800, 1))
            farmer.crop = "Cotton"
            self.assertEqual(recall(db, farmer), ("", 1))
        engine.dispose()

    def test_transcript_survives_speech_output_failure(self):
        db = Mock()
        with patch("api.routes.convert_ogg_to_wav", return_value=None) as convert, patch("api.routes.transcribe_voice", return_value=("बारिश होगी?", "hi")), patch("api.routes.advise", return_value={"response": "उत्तर"}), patch("api.routes.text_to_speech", return_value=None):
            convert.side_effect = lambda path: path
            result = voice(1, UploadFile(file=io.BytesIO(b"sample")), db)
        self.assertEqual(result, {"response": "उत्तर", "transcribed": "बारिश होगी?"})
