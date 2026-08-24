from __future__ import annotations
import logging
import re

from database.medicine import get_medicine, DISEASE_ALIASES
from services.rag_service import search_rag
from services.ai_service import get_ai_fallback_treatment, get_rag_treatment

log = logging.getLogger(__name__)

RAG_MIN_SCORE    = 0.45
CROP_MATCH_BONUS = 0.08

# Sorted once at load — not on every call
_SORTED_ALIASES = sorted(
    DISEASE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True
)


# ── Text helpers ──────────────────────────────────────────────────────────────

def _clean_disease_text(text: str) -> str:
    """
    FIX 2: Normalise punctuation before alias matching.
    'leaf-blight', 'leaf/blight', 'leaf,blight' all become 'leaf blight'.
    """
    text = text.lower().strip()
    text = re.sub(r"[-/,;|]+", " ", text)      # hyphens, slashes, commas → space
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _alias_match(alias: str, text: str) -> bool:
    """
    FIX 1: Word-boundary aware matching — prevents short aliases overmatching.
    e.g. alias 'rot' must NOT match inside 'protein' or 'carrot mosaic'.
    """
    pattern = r"\b" + re.escape(alias) + r"\b"
    return bool(re.search(pattern, text))


def _normalize_confidence(raw: str) -> str:
    """
    FIX 5: Coerce whatever upstream sends to a canonical value.
    'LOW', 'low', 'MEDIUM', or anything invalid → 'Low' / 'Medium' / 'High'.
    """
    normalised = str(raw).strip().title()
    return normalised if normalised in {"High", "Medium", "Low"} else "Low"


def _escape_md(text: str) -> str:
    """
    FIX 6: Escape Telegram Markdown v1 special chars in product field values.
    Prevents formatting breaks when chemical names contain _, *, ` or [.
    """
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text


# ── Crop–disease plausibility check ──────────────────────────────────────────
# FIX 3: Most important missing safeguard in the file.
# Maps crops to the crop-identifying keywords that appear inside disease names.
# "rice blast" → contains "rice" → implausible for a wheat farmer.
# Generic diseases ("powdery mildew", "damping off") contain no crop keyword
# → always pass as plausible.

_CROP_KEYWORDS: dict[str, set[str]] = {
    "rice":       {"rice", "paddy"},
    "wheat":      {"wheat"},
    "cotton":     {"cotton"},
    "tomato":     {"tomato"},
    "potato":     {"potato"},
    "sugarcane":  {"sugarcane", "cane"},
    "maize":      {"maize", "corn"},
    "groundnut":  {"groundnut", "peanut"},
    "soybean":    {"soybean", "soya"},
    "chilli":     {"chilli", "chili", "pepper"},
    "onion":      {"onion"},
    "mango":      {"mango"},
    "banana":     {"banana"},
    "citrus":     {"citrus", "orange", "lemon"},
}


def _is_plausible_for_crop(disease: str, crop: str) -> bool:
    """
    Returns False only when the disease name explicitly names a DIFFERENT crop.

    Examples:
      disease='rice blast',     crop='wheat'  → False  (flagged)
      disease='early blight',   crop='wheat'  → True   (generic — passes)
      disease='wheat rust',     crop='wheat'  → True   (same crop — passes)
      disease='citrus canker',  crop='rice'   → False  (flagged)
    """
    disease_lower  = disease.lower()
    crop_lower     = crop.lower().strip()
    farmer_keywords = _CROP_KEYWORDS.get(crop_lower, set())

    for other_crop, keywords in _CROP_KEYWORDS.items():
        if other_crop == crop_lower:
            continue
        for kw in keywords:
            if _alias_match(kw, disease_lower):
                # Disease mentions another crop's keyword.
                # Only flag if the farmer's own crop keywords are NOT present.
                if not any(_alias_match(fk, disease_lower) for fk in farmer_keywords):
                    return False
    return True


# ── Filler words for normalisation ────────────────────────────────────────────

_FILLER_WORDS = {
    "disease", "infection", "problem", "issue", "attack",
    "severe", "moderate", "mild", "symptoms", "symptom",
    "suspected", "possible", "likely", "confirmed",
    "stage", "advanced", "chronic", "acute",
}


def _normalize_disease_name(raw: str) -> str:
    """
    Normalise a disease name before DB/RAG lookup.
    Uses _clean_disease_text() and _alias_match() for safe, consistent matching.
    """
    if not raw:
        return ""
    cleaned = _clean_disease_text(raw)

    # Pass 1 — alias match on punctuation-normalised text
    for alias, canonical in _SORTED_ALIASES:
        if _alias_match(alias, cleaned):
            return canonical

    # Strip filler words
    tokens  = [t for t in cleaned.split() if t not in _FILLER_WORDS]
    cleaned = " ".join(tokens).strip()

    # Pass 2 — alias match after filler cleanup
    for alias, canonical in _SORTED_ALIASES:
        if _alias_match(alias, cleaned):
            return canonical

    return cleaned


# ── Disease extraction (legacy string format support) ─────────────────────────

def extract_disease_name(ai_output: str) -> str:
    if not ai_output:
        return ""
    for line in ai_output.strip().splitlines():
        line = line.strip()
        if line.lower().startswith("disease:"):
            name = line.split(":", 1)[1].strip()
            if name:
                return name.lower()
    match = re.search(r"disease:\s*(.+)", ai_output, re.I)
    return match.group(1).strip().lower() if match else ""


# ── Response formatters ───────────────────────────────────────────────────────

def _format_dataset_result(data: dict, confidence: str = "") -> str:
    top = data.get("recommended_products", [])[:3]
    if not top:
        return "\n⚠️ Medicine data found but no products listed.\n"

    header = "\n\n💊 *Verified Treatment (Local Database):*\n"
    if confidence == "Low":
        header += "⚠️ _Diagnosis confidence is Low — confirm with a local expert before spraying._\n"

    result = header
    for i, p in enumerate(top, 1):
        # FIX 6: escape field values before embedding in Markdown
        ingredient  = _escape_md(p.get("active_ingredient", "N/A"))
        formulation = _escape_md(p.get("formulation",       "N/A"))
        dosage      = _escape_md(p.get("dosage",            "N/A"))
        water       = _escape_md(p.get("water_dilution",    "N/A"))
        waiting     = _escape_md(p.get("waiting_period",    "N/A"))
        result += (
            f"\n*{i}.* {ingredient} ({formulation})"
            f"\n • Dosage: {dosage}"
            f"\n • Water: {water}"
            f"\n • Waiting period: {waiting}\n"
        )
    return result


def _format_rag_header(disease: str, confidence: str = "") -> str:
    header = f"\n\n🔍 *Treatment for {_escape_md(disease.title())}* (CIBRC/ICAR Knowledge Base):\n"
    if confidence == "Low":
        header += "⚠️ _Diagnosis confidence is Low — confirm with a local expert before spraying._\n"
    return header


# ── Core RAG search ───────────────────────────────────────────────────────────

def _run_rag_search(disease: str, crop: str) -> tuple[str | None, float]:
    try:
        results = search_rag(disease=disease, crop=crop, n_results=3)
    except Exception as exc:
        log.warning("RAG search failed: %s", exc)
        return None, 0.0

    if not results:
        return None, 0.0

    best     = results[0]
    score    = float(best.get("composite_score", 0.0))
    metadata = best.get("metadata", {}) or {}
    doc_crop = str(metadata.get("crop", "")).lower().strip()

    if doc_crop and (doc_crop in crop.lower() or crop.lower() in doc_crop):
        score += CROP_MATCH_BONUS

    if score < RAG_MIN_SCORE:
        log.info(
            "RAG score %.3f below threshold %.2f for disease='%s' crop='%s'",
            score, RAG_MIN_SCORE, disease, crop,
        )
        return None, 0.0

    context_parts = [r["document"] for r in results[:3] if r.get("document")]
    return ("\n\n---\n\n".join(context_parts), score) if context_parts else (None, 0.0)


# ── Main public function ──────────────────────────────────────────────────────

def get_medicine_recommendation(
    crop:     str,
    ai_text:  str | dict,
    location: str = "",
) -> dict:
    """
    3-tier medicine lookup pipeline.

    ai_text: dict (new ai_service.py) or str (legacy format).

    Returns:
      { "status", "text", "disease", "confidence" }
    """
    # Extract disease + confidence from dict or legacy string
    if isinstance(ai_text, dict):
        raw_disease = ai_text.get("disease", "").strip().lower()
        confidence  = _normalize_confidence(ai_text.get("confidence", "Low"))   # FIX 5
    else:
        raw_disease = extract_disease_name(ai_text).strip().lower()
        confidence  = "Medium"

    _no_disease = {"unclear symptoms", "unclear image", "not a crop image", "unknown", ""}
    if not raw_disease or raw_disease in _no_disease:
        return {
            "status":     "disease_not_found",
            "text":       "\n⚠️ Could not identify disease clearly.\nUsing AI guidance below.\n",
            "disease":    None,
            "confidence": confidence,
        }

    disease        = _normalize_disease_name(raw_disease)
    crop_clean     = crop.lower().strip()
    location_clean = (location or "").strip()

    # FIX 3: crop–disease plausibility check before any lookup
    if not _is_plausible_for_crop(disease, crop_clean):
        log.warning(
            "Crop-disease mismatch: disease='%s' is implausible for crop='%s'",
            disease, crop_clean,
        )
        return {
            "status":     "disease_not_found",
            "text":       (
                f"\n⚠️ *Diagnosis mismatch detected.*\n"
                f"The identified disease (*{_escape_md(disease.title())}*) does not match "
                f"your registered crop (*{_escape_md(crop_clean.title())}*).\n"
                f"Please re-describe your symptoms or send a clearer image.\n"
            ),
            "disease":    disease,
            "confidence": "Low",
        }

    log.info(
        "Lookup | crop='%s' | disease='%s' | confidence='%s' | location='%s'",
        crop_clean, disease, confidence, location_clean,
    )

    # ── Tier 1: Structured local dataset ─────────────────────────────────
    try:
        data = get_medicine(crop_clean, disease)
    except Exception as exc:
        log.error("get_medicine failed: %s", exc)
        data = None

    if data:
        log.info("Tier 1 HIT for '%s'", disease)
        return {
            "status":     "found_dataset",
            "text":       _format_dataset_result(data, confidence),
            "disease":    disease,
            "confidence": confidence,
        }

    # ── Tier 2: RAG semantic search ───────────────────────────────────────
    rag_context, rag_score = _run_rag_search(disease, crop_clean)
    if rag_context:
        log.info("Tier 2 RAG HIT | disease='%s' | score=%.3f", disease, rag_score)
        try:
            rag_text = get_rag_treatment(
                crop=crop_clean,
                location=location_clean,
                disease=disease,
                rag_context=rag_context,
            )
        except Exception as exc:
            log.warning("get_rag_treatment failed: %s", exc)
            # FIX 4: clean message instead of raw backend context dump
            rag_text = (
                "⚠️ Could not format treatment details right now.\n"
                "Please consult your local KVK or agriculture officer for guidance."
            )
        return {
            "status":     "found_rag",
            "text":       _format_rag_header(disease, confidence) + rag_text,
            "disease":    disease,
            "confidence": confidence,
        }

    # ── Tier 3: AI fallback ───────────────────────────────────────────────
    log.info("Tier 3 AI fallback for '%s'", disease)
    try:
        fallback_text = get_ai_fallback_treatment(
            crop=crop_clean,
            location=location_clean,
            disease=disease,
        )
    except Exception as exc:
        log.error("get_ai_fallback_treatment failed: %s", exc)
        fallback_text = (
            "⚠️ Sorry, treatment guidance could not be generated right now.\n"
            "Please consult your local KVK or agriculture officer before spraying."
        )

    return {
        "status":     "fallback",
        "text":       "\n⚠️ *Not found in verified database or knowledge base.*\n\n" + fallback_text,
        "disease":    disease,
        "confidence": confidence,
    }