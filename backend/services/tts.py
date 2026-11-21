from app.core.config import settings
from services.voice_service import text_to_speech as synthesize


def text_to_speech(text, language):
    if settings.TTS_PROVIDER != "gtts":
        return None
    return synthesize(text, language)
