"""
services/rag_service.py
Semantic search over the ChromaDB vector store.

Public API
----------
search_rag(disease, crop, n_results) -> list[dict]
rag_health_check()                   -> dict
"""

from __future__ import annotations
import logging
import os
import re
import threading
import time

log = logging.getLogger(__name__)

CHROMA_DIR   = os.getenv("CHROMA_DIR", os.path.join("database", "chroma_db"))
COLLECTION   = "medicines"
EMBED_MODEL  = "all-MiniLM-L6-v2"

# FIX 1: MIN_SIMILARITY is now applied to composite_score AFTER reranking,
# not to raw cosine score before reranking.  A result with low raw cosine
# but exact crop + disease metadata can now survive where it was silently
# dropped before.
MIN_SIMILARITY = 0.45

_model      = None
_collection = None
_load_lock  = threading.Lock()

_load_failures:     int   = 0
_last_failure_time: float = 0.0
_MAX_LOAD_FAILURES  = 3
_RETRY_COOLDOWN_SEC = 60.0

_CROP_EXACT_BONUS   = 0.10
_DISEASE_NAME_BONUS = 0.08

# FIX 2: alias table imported once at module load.
# Used by _disease_overlap() for canonical normalisation before comparison.
# Falls back to empty dict if database.medicine is not importable (test env).
try:
    from database.medicine import DISEASE_ALIASES as _DISEASE_ALIASES
    # Pre-sort longest alias first — same pattern as medicine_service.py
    _SORTED_ALIASES: list[tuple[str, str]] = sorted(
        _DISEASE_ALIASES.items(), key=lambda x: len(x[0]), reverse=True
    )
except Exception:  # pragma: no cover
    log.warning("Could not import DISEASE_ALIASES — disease reranking uses raw text")
    _SORTED_ALIASES = []


# ── Loader (unchanged) ────────────────────────────────────────────────────────

def _should_attempt_load() -> bool:
    if _model is not None:
        return False
    if _load_failures >= _MAX_LOAD_FAILURES:
        return False
    if _load_failures > 0:
        elapsed = time.monotonic() - _last_failure_time
        if elapsed < _RETRY_COOLDOWN_SEC:
            return False
    return True


def _load() -> None:
    global _model, _collection, _load_failures, _last_failure_time

    if not _should_attempt_load():
        return

    with _load_lock:
        if not _should_attempt_load():
            return

        try:
            from sentence_transformers import SentenceTransformer
            import chromadb

            os.environ["ANONYMIZED_TELEMETRY"] = "False"

            log.info("Loading embedding model: %s (attempt %d/%d)",
                     EMBED_MODEL, _load_failures + 1, _MAX_LOAD_FAILURES)
            _model = SentenceTransformer(EMBED_MODEL)

            log.info("Connecting to ChromaDB at: %s", CHROMA_DIR)
            client = chromadb.PersistentClient(path=CHROMA_DIR)
            _collection = client.get_collection(COLLECTION)

            _load_failures     = 0
            _last_failure_time = 0.0
            log.info("RAG ready — %d docs indexed", _collection.count())

        except Exception as exc:
            _load_failures    += 1
            _last_failure_time = time.monotonic()
            _model             = None
            _collection        = None

            if _load_failures >= _MAX_LOAD_FAILURES:
                log.error("RAG load failed %d/%d times — giving up: %s",
                          _load_failures, _MAX_LOAD_FAILURES, exc)
            else:
                log.warning("RAG load failed (%d/%d) — retry in %.0fs: %s",
                            _load_failures, _MAX_LOAD_FAILURES,
                            _RETRY_COOLDOWN_SEC, exc)


# ── Query builder (unchanged) ─────────────────────────────────────────────────

def _build_query(crop: str, disease: str) -> str:
    return (
        f"crop: {crop.strip().lower()} | "
        f"disease: {disease.strip().lower()} | "
        f"treatments: pesticide fungicide dosage India"
    )


# ── Distance converter (unchanged) ────────────────────────────────────────────

def _cosine_distance_to_similarity(distance: float) -> float:
    return round(max(0.0, 1.0 - (distance / 2.0)), 4)


# ── Disease canonicaliser ─────────────────────────────────────────────────────

def _canonical(name: str) -> str:
    """
    FIX 2 (part a): Map a disease name to its canonical alias if one exists.
    Uses the same DISEASE_ALIASES table as medicine_service._normalize_disease_name()
    so both layers agree on what the disease is called.

    Falls back to the cleaned input text if no alias matches.
    """
    text = re.sub(r"[-/,;|]+", " ", name.lower().strip())
    text = re.sub(r"\s+", " ", text).strip()

    for alias, canonical in _SORTED_ALIASES:
        if re.search(r"\b" + re.escape(alias) + r"\b", text):
            return canonical

    return text


def _disease_overlap(issue_name: str, disease: str) -> bool:
    """
    FIX 2 (part b): Replace bare substring check with alias-normalised comparison.

    Both issue_name (from ChromaDB metadata) and disease (from AI output)
    are first mapped to their canonical forms, then compared with word-boundary
    matching — the same approach used in medicine_service._alias_match().

    This means:
      - "early blight" == "alternaria blight"  if they share a canonical alias
      - "leaf blight"  ≠ "blast"               (no alias relationship)
      - short aliases cannot match inside unrelated words

    Without this, substring matching would grant the bonus to unrelated diseases
    that happen to share a common word.
    """
    canon_issue   = _canonical(issue_name)
    canon_disease = _canonical(disease)

    # Exact canonical match — strongest signal
    if canon_issue == canon_disease:
        return True

    # Word-boundary containment — one is a specialisation of the other
    # e.g. canon_issue="early blight", canon_disease="blight"
    if re.search(r"\b" + re.escape(canon_disease) + r"\b", canon_issue):
        return True
    if re.search(r"\b" + re.escape(canon_issue) + r"\b", canon_disease):
        return True

    return False


# ── Metadata-aware reranker ───────────────────────────────────────────────────

def _rerank(results: list[dict], disease: str, crop: str) -> list[dict]:
    """
    FIX 1 + FIX 2: Apply metadata bonuses, then sort by composite_score.
    Filtering by MIN_SIMILARITY now happens in search_rag() AFTER this step,
    using composite_score — not raw cosine score.

    Bonuses (additive, capped at 1.0):
      +_CROP_EXACT_BONUS   — metadata crop exactly matches farmer's crop
      +_DISEASE_NAME_BONUS — metadata issue_name matches via alias-normalised
                             comparison (not bare substring)
    """
    crop_lower = crop.strip().lower()

    for r in results:
        meta      = r.get("metadata") or {}
        composite = r["score"]

        doc_crop = str(meta.get("crop", "")).strip().lower()
        if doc_crop and doc_crop == crop_lower:
            composite += _CROP_EXACT_BONUS

        issue_name = str(meta.get("issue_name", "")).strip()
        if issue_name and _disease_overlap(issue_name, disease):   # FIX 2
            composite += _DISEASE_NAME_BONUS

        r["composite_score"] = round(min(composite, 1.0), 4)

    return sorted(results, key=lambda x: x["composite_score"], reverse=True)


# ── Public: semantic search ───────────────────────────────────────────────────

def search_rag(disease: str, crop: str = "", n_results: int = 3) -> list[dict]:
    """
    Semantic search over the ChromaDB medicine vector store.

    Each result dict:
      {
        "document"        : str,
        "score"           : float,   # raw cosine similarity (preserved)
        "composite_score" : float,   # cosine + metadata bonuses (filter key)
        "metadata"        : { crop, issue_name, category, ingredient_str,
                              aliases, source,
                              dosage*, waiting_period*, water_dilution*, source_pdf* }
      }

    Returns [] if DB unavailable, disease blank, or no result passes threshold.
    """
    if not disease or not disease.strip():
        log.warning("search_rag called with empty disease — returning []")
        return []

    _load()

    if _collection is None or _model is None:
        log.warning("search_rag: DB not loaded — returning []")
        return []

    doc_count = _collection.count()
    if doc_count == 0:
        log.warning("search_rag: collection is empty — returning []")
        return []

    query_text = _build_query(crop, disease)

    try:
        query_embedding = _model.encode(query_text).tolist()
        raw = _collection.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, doc_count),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        log.error("ChromaDB query failed: %s", exc)
        return []

    documents = raw.get("documents", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]
    distances = raw.get("distances", [[]])[0]

    # Collect ALL non-None results — do NOT filter by score yet (FIX 1)
    candidates: list[dict] = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        if doc is None or meta is None:
            continue
        candidates.append({
            "document": doc,
            "score":    _cosine_distance_to_similarity(dist),
            "metadata": meta,
        })

    # Rerank first, THEN filter by composite_score (FIX 1)
    reranked = _rerank(candidates, disease, crop)
    results  = [r for r in reranked if r["composite_score"] >= MIN_SIMILARITY]

    log.info(
        "query='%s' → %d/%d passed composite threshold=%.2f",
        query_text[:70], len(results), len(candidates), MIN_SIMILARITY,
    )

    return results


# ── Public: health check (unchanged) ─────────────────────────────────────────

def rag_health_check() -> dict:
    _load()

    if _collection is None:
        return {
            "status":    "error",
            "doc_count": 0,
            "model":     EMBED_MODEL,
            "error":     (
                f"ChromaDB failed to load "
                f"({_load_failures}/{_MAX_LOAD_FAILURES} attempts) — "
                f"run scripts/build_vector_db.py first"
            ),
        }

    return {
        "status":    "ok",
        "doc_count": _collection.count(),
        "model":     EMBED_MODEL,
    }