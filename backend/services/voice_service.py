"""
services/voice_service.py
Voice processing — OGG→WAV conversion (ffmpeg), Whisper STT, gTTS TTS.
"""
from __future__ import annotations
import logging
import os
import subprocess
import tempfile
import threading

log = logging.getLogger(__name__)



# ── Gemini API client (for STT) ────────────────────────────────────────────────

from services.model_runtime import generate
from config import AUDIO_MODEL


# ── Language resolution ────────────────────────────────────────────────────────
# Two-layer lookup: ISO code first (Whisper output), full-name fallback (legacy).

_ISO_TO_GTTS: dict[str, str] = {
    "en": "en",
    "hi": "hi",
    "ta": "ta",
    "te": "te",
    "kn": "kn",
    "ml": "ml",
    "bn": "bn",
    "mr": "mr",
    "gu": "gu",
    "pa": "pa",
    "ur": "ur",
    "or": "or",
    "as": "as",
    "ne": "ne",
}

_NAME_TO_ISO: dict[str, str] = {
    "english":       "en",
    "hindi":         "hi",
    "tamil":         "ta",
    "telugu":        "te",
    "kannada":       "kn",
    "malayalam":     "ml",
    "bengali":       "bn",
    "marathi":       "mr",
    "gujarati":      "gu",
    "punjabi":       "pa",
    "urdu":          "ur",
    "odia":          "or",
    "assamese":      "as",
    "nepali":        "ne",
    "bhojpuri":      "hi",
    "rajasthani":    "hi",
    "haryanvi":      "hi",
    "maithili":      "hi",
    "chhattisgarhi": "hi",
    "magahi":        "hi",
}

_GTTS_MAX_CHARS = 5000


def _resolve_gtts_lang(language: str) -> str:
    """
    Resolve any language identifier to a valid gTTS code.
    Accepts ISO codes ("hi", "ta") or full names ("hindi", "tamil").
    Falls back to "en" for anything unknown.
    """
    if not language:
        return "en"
    lang = language.strip().lower()
    if lang in _ISO_TO_GTTS:
        return _ISO_TO_GTTS[lang]
    iso = _NAME_TO_ISO.get(lang)
    if iso:
        return _ISO_TO_GTTS.get(iso, "en")
    return "en"


# ── OGG → WAV ─────────────────────────────────────────────────────────────────

def convert_ogg_to_wav(ogg_path: str) -> str | None:
    """
    Convert OGG voice note to 16 kHz mono WAV for Whisper.
    Uses os.splitext() — not str.replace — to build the output path safely.
    timeout=30 prevents ffmpeg hanging on corrupt audio files.
    """
    try:
        base, _ = os.path.splitext(ogg_path)
        wav_path = base + ".wav"
        subprocess.run(
            [
                "ffmpeg", "-i", ogg_path,
                "-ar", "16000",
                "-ac", "1",
                "-y", wav_path,
            ],
            capture_output=True,
            check=True,
            timeout=30,
        )
        log.info("Converted to WAV: %s", wav_path)
        return wav_path

    except subprocess.TimeoutExpired:
        log.error("FFmpeg timed out on: %s", ogg_path)
        return None
    except subprocess.CalledProcessError as e:
        log.error("FFmpeg error: %s", e.stderr.decode(errors="replace"))
        return None
    except FileNotFoundError:
        log.error("FFmpeg not found — install ffmpeg")
        return None



# ── Whisper STT via Gemini ────────────────────────────────────────────────────

def transcribe_voice(audio_file_path: str) -> tuple[str | None, str | None]:
    """
    Transcribe a WAV file using Gemini's audio understanding.
    Returns (text, language_iso_code) or (None, None) on failure.
    """
    try:
        provider = os.getenv("STT_PROVIDER") or ("groq" if AUDIO_MODEL.startswith("groq/") else "gemini")
        if provider == "groq":
            from groq import Groq
            with open(audio_file_path, "rb") as audio:
                transcript = Groq(timeout=45, max_retries=1).audio.transcriptions.create(
                    file=audio, model=os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo"), response_format="verbose_json")
            return transcript.text.strip() or None, transcript.language

        with open(audio_file_path, "rb") as f:
            audio_bytes = f.read()

        raw = generate("Transcribe the spoken language without translating or answering.",
                       "Return the transcript followed by [lang: ISO language code].",
                       spec=AUDIO_MODEL, media=("audio", "audio/wav", audio_bytes), max_tokens=1600)

        # Extract language tag if present
        language = "en"
        if "[lang:" in raw:
            parts = raw.rsplit("[lang:", 1)
            raw = parts[0].strip()
            lang_part = parts[1].replace("]", "").strip()
            if lang_part:
                language = lang_part

        text = raw.strip()
        if not text:
            log.warning("Empty transcription for: %s", audio_file_path)
            return None, None

        log.info("Transcription completed")
        return text, language

    except Exception as e:
        log.error("Transcription error: %s", e)
        return None, None



# ── gTTS TTS ──────────────────────────────────────────────────────────────────

def text_to_speech(text: str, language: str = "en") -> str | None:
    """
    Convert text to speech using gTTS. Returns path to MP3 temp file.
    _resolve_gtts_lang() accepts both ISO codes and full language names.
    Text is truncated to _GTTS_MAX_CHARS to prevent silent gTTS failures
    on long AI responses.
    """
    try:
        from gtts import gTTS

        lang_code = _resolve_gtts_lang(language)
        text      = text.strip()[:_GTTS_MAX_CHARS]

        if not text:
            log.warning("text_to_speech: empty text — skipping")
            return None

        tmp      = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp_path = tmp.name
        tmp.close()

        tts = gTTS(text=text, lang=lang_code, slow=False)
        tts.save(tmp_path)
        log.info("TTS saved: %s (lang=%s)", tmp_path, lang_code)
        return tmp_path

    except Exception as e:
        log.error("TTS error: %s", e)
        return None


# ── Temp file cleanup ─────────────────────────────────────────────────────────

def cleanup_file(file_path: str | None) -> None:
    """Delete a temporary audio file. Silent no-op if path is None or missing."""
    if not file_path:
        return
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        log.warning("Cleanup error for %s: %s", file_path, e)
