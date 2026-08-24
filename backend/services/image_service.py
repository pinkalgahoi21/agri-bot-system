"""
services/image_service.py
Vision inference for crop disease diagnosis.

Returns a DiseaseResult-validated dict — same schema as identify_disease()
in ai_service.py. Both pipelines share one canonical validator.
"""
from __future__ import annotations
import base64
import io
import logging
import os
import time

import groq
from groq import Groq
from config import GROQ_API_KEY

from services.ai_service import DiseaseResult, _DISEASE_FALLBACK

log = logging.getLogger(__name__)

VISION_MODEL     = "meta-llama/llama-4-scout-17b-16e-instruct"
_MAX_IMAGE_BYTES = 1_000_000   # 1 MB post-compression
_MAX_DIM         = 1024

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY or not GROQ_API_KEY.strip():
            raise RuntimeError("GROQ_API_KEY not configured")
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


# ── MIME detection ────────────────────────────────────────────────────────────

def _detect_mime(data: bytes) -> str:
    """Content-based MIME detection via magic bytes."""
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    return "image/jpeg"


# ── Image compression ─────────────────────────────────────────────────────────

def _compress_image(image_path: str) -> tuple[bytes, str]:
    """
    Resize to _MAX_DIM and JPEG-compress until under _MAX_IMAGE_BYTES.
    Raises RuntimeError if Pillow is absent and the image is too large.
    """
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")

            if max(img.size) > _MAX_DIM:
                img.thumbnail((_MAX_DIM, _MAX_DIM), Image.LANCZOS)
                log.info("Image resized to %s", img.size)

            for quality in (85, 70, 55, 40):
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality, optimize=True)
                data = buf.getvalue()                    # FIX: capture before any seek
                if len(data) <= _MAX_IMAGE_BYTES:
                    log.info("Compressed to %d bytes (quality=%d)", len(data), quality)
                    return data, "image/jpeg"

            # quality=40 was last attempt — return it regardless of size
            log.warning("Could not compress below %d bytes — sending at quality=40", _MAX_IMAGE_BYTES)
            return data, "image/jpeg"                   # FIX: data already set above

    except ImportError:
        with open(image_path, "rb") as f:
            raw = f.read()
        if len(raw) > _MAX_IMAGE_BYTES:
            raise RuntimeError(
                f"Pillow is not installed and the image is too large "
                f"({len(raw):,} bytes > {_MAX_IMAGE_BYTES:,} bytes limit). "
                f"Install Pillow: pip install pillow"
            )
        log.warning("Pillow not installed — sending raw image (%d bytes)", len(raw))
        return raw, _detect_mime(raw)


# ── Output parser ─────────────────────────────────────────────────────────────

def _parse_vision_output(raw: str) -> dict:
    """
    Parse structured plain text from vision model into a validated dict.

    Tracks defaulted fields — forces confidence=Low if too many fields
    fall back, so bad responses surface honestly.
    """
    lines = raw.strip().splitlines()

    # ── Extract identified_crop BEFORE trimming to Disease: line ─────────────
    identified_crop = "unknown"
    for line in lines:
        if line.strip().lower().startswith("identified crop:") and ":" in line:
            identified_crop = line.split(":", 1)[1].strip().lower()
            break

    # FIX 1: model sometimes returns "Not Sugarcane" / "Not_Tomato" instead of
    # the actual plant name. These are comparative, not descriptive.
    # Force to "unknown" so mismatch detection fires correctly.
    _ic = identified_crop.replace("_", " ").replace("-", " ")
    if (
        _ic.startswith("not ") or
        identified_crop.startswith("not_") or
        identified_crop == "not"
    ):
        log.warning(
            "[vision] Model returned comparative crop name '%s' — forcing unknown",
            identified_crop,
        )
        identified_crop = "unknown"

    # FIX 2: explicit guard for not_a_plant variants
    # model may return "not a plant", "not_a_plant", "no plant", etc.
    _no_plant_variants = {"not_a_plant", "not a plant", "no plant", "not plant"}
    if _ic in _no_plant_variants or identified_crop in _no_plant_variants:
        identified_crop = "not_a_plant"

    # Trim junk above Disease: line
    start = 0
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("disease:"):
            start = i
            break
    lines = lines[start:]

    defaulted: set[str] = set()

    def _extract(prefix: str, field: str, fallback: str) -> str:
        for line in lines:
            if line.strip().lower().startswith(prefix.lower()) and ":" in line:
                value = line.split(":", 1)[1].strip()
                if value:
                    return value
        defaulted.add(field)
        return fallback

    # Parse prevention bullet points
    prevention: list[str] = []
    in_prevention = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("prevention"):
            in_prevention = True
            continue
        if in_prevention:
            if stripped.startswith(("•", "-", "*")):
                point = stripped.lstrip("•-* ").strip()
                if point:
                    prevention.append(point)
            elif stripped and ":" in stripped and not stripped[0].isspace():
                in_prevention = False
    if not prevention:
        defaulted.add("prevention")
        prevention = ["Monitor crop closely", "Consult local KVK"]

    # Normalise controlled-vocabulary fields
    raw_conf   = _extract("Confidence", "confidence", "").title()
    confidence = raw_conf if raw_conf in {"High", "Medium", "Low"} else "Low"
    if raw_conf not in {"High", "Medium", "Low"}:
        defaulted.add("confidence")

    raw_sev  = _extract("Severity", "severity", "").title()
    severity = raw_sev if raw_sev in {"Mild", "Moderate", "Severe"} else "Unknown"
    if raw_sev not in {"Mild", "Moderate", "Severe"}:
        defaulted.add("severity")

    raw_urg = _extract("Urgency", "urgency", "").lower()
    urgency_map = {
        "immediate":     "Immediate",
        "within a week": "Within a week",
        "monitor":       "Monitor",
    }
    urgency = urgency_map.get(raw_urg, "Monitor")
    if raw_urg not in urgency_map:
        defaulted.add("urgency")

    disease = _extract("Disease", "disease", "").strip()
    if not disease:
        disease = "Unclear symptoms"

    cause = _extract("Cause", "cause", "Could not determine cause.").strip()

    # Downgrade confidence honestly if too many fields defaulted
    if len(defaulted) >= 3:
        log.warning(
            "Vision parse: %d fields defaulted (%s) — forcing confidence=Low",
            len(defaulted), ", ".join(sorted(defaulted)),
        )
        confidence = "Low"

    parsed = {
        "disease":    disease,
        "confidence": confidence,
        "severity":   severity,
        "cause":      cause,
        "prevention": prevention,
        "urgency":    urgency,
    }

    try:
        result = DiseaseResult(**parsed).model_dump()
        result["identified_crop"] = identified_crop
        return result
    except Exception as e:
        log.warning("DiseaseResult validation failed on vision output: %s", e)
        fallback = _DISEASE_FALLBACK.copy()
        fallback["identified_crop"] = "unknown"
        return fallback


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_crop_image(image_path: str, profile: dict) -> dict | None:
    """
    Analyse a crop image and return a validated disease diagnosis dict.
    Dict schema is DiseaseResult-validated + 'identified_crop' field.
    Returns None only if the API call fails after all retries.
    """
    location = profile.get("location", "India")

    if not os.path.isfile(image_path):
        log.error("File not found: %s", image_path)
        return None

    try:
        image_bytes, mime_type = _compress_image(image_path)
    except RuntimeError as e:
        log.error("Image compression failed: %s", e)
        return None

    b64      = base64.b64encode(image_bytes).decode("utf-8")
    data_url = f"data:{mime_type};base64,{b64}"

    # NOTE: Registered crop intentionally excluded from prompt.
    # Providing it biases the model — produces "Not_Sugarcane" instead
    # of "Potato". Model must describe what it SEES, uninfluenced.
    prompt = f"""You are an expert agricultural advisor for Indian farmers.

Farmer details:
- Location: {location}

Analyse the crop image provided.

STRICT OUTPUT FORMAT (copy exactly — no changes, no extra lines before):

Identified Crop: <COMMON name of the plant you SEE — e.g. wheat, rice, tomato>
Disease: <name>
Confidence: <High or Medium or Low>
Severity: <Mild or Moderate or Severe>
Cause: <one-line cause>
Prevention:
• <point>
• <point>
• <point>
Urgency: <Immediate or Within a week or Monitor>

STRICT RULES:
- Line 1 MUST be "Identified Crop: " — COMMON name only (wheat NOT Triticum Aestivum)
- Write what you DO see — NEVER write "Not [crop]" or "Not_[crop]"
- If you cannot identify the plant: Identified Crop: unknown
- If the image has NO plant at all: Identified Crop: not_a_plant
- Line 2 MUST start with exactly "Disease: " (no emoji, no blank line)
- ONE disease or pest only — the single most likely
- If image is blurry/unclear: Disease: Unclear image
- NO medicine or pesticide suggestions
- Keep entire response under 220 words"""

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            response = _get_client().chat.completions.create(
                model=VISION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a plant pathologist analysing crop images. "
                            "Line 1 MUST be 'Identified Crop: <common name>'. "
                            "Use COMMON names only — never scientific/Latin names. "
                            "Write what you SEE — never 'Not [something]'. "
                            "If unsure: Identified Crop: unknown. "
                            "Never suggest medicines or pesticides."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text",      "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                temperature=0.2,
                max_tokens=350,
                timeout=20.0,
            )

            raw = response.choices[0].message.content.strip()
            log.info("Vision raw output:\n%s", raw)
            return _parse_vision_output(raw)

        except groq.RateLimitError as e:
            last_exc = e
            wait = 2.0 * (attempt + 1)
            log.warning("Rate limit — retry %d/3 in %.1fs", attempt + 1, wait)
            time.sleep(wait)

        except groq.APITimeoutError as e:
            last_exc = e
            log.warning("Vision API timeout — retry %d/3", attempt + 1)
            time.sleep(0.5)

        except groq.AuthenticationError:
            log.error("Groq auth failed — check GROQ_API_KEY")
            return None

        except Exception as e:
            log.error("Vision API error: %s", e)
            return None

    log.error("Vision API failed after 3 attempts: %s", last_exc)
    return None