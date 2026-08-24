"""
services/rag_service.py
Lightweight medicine lookup using the local database.
"""

from __future__ import annotations
import logging
from database.medicine import MEDICINE_DB, normalize_disease

log = logging.getLogger(__name__)

def search_rag(disease: str, crop: str = "", n_results: int = 3) -> list[dict]:
    """
    Lightweight search over the MEDICINE_DB dictionary.
    Replaces the old ChromaDB semantic search to save RAM.
    """
    if not disease or not disease.strip():
        log.warning("search_rag called with empty disease — returning []")
        return []

    crop_key = crop.strip().lower()
    disease_key = normalize_disease(disease)

    results = []

    # If we have the exact crop in our database
    if crop_key in MEDICINE_DB:
        crop_db = MEDICINE_DB[crop_key]
        
        # Look for the exact disease match
        if disease_key in crop_db:
            data = crop_db[disease_key]
            for product in data.get("recommended_products", []):
                doc_str = f"Crop: {crop_key.title()} | Disease: {disease_key.title()} | Product: {product.get('active_ingredient')} ({product.get('formulation')})"
                results.append({
                    "document": doc_str,
                    "metadata": {
                        "crop": crop_key,
                        "issue_name": disease_key,
                        "category": data.get("category", "unknown"),
                        **product
                    }
                })

    # If we didn't find it for the specific crop, let's search across all crops just in case
    # (Many diseases like 'aphids' share treatments across crops)
    if not results:
        for db_crop, db_diseases in MEDICINE_DB.items():
            if disease_key in db_diseases:
                data = db_diseases[disease_key]
                for product in data.get("recommended_products", []):
                    doc_str = f"Crop: {db_crop.title()} | Disease: {disease_key.title()} | Product: {product.get('active_ingredient')} ({product.get('formulation')})"
                    results.append({
                        "document": doc_str,
                        "metadata": {
                            "crop": db_crop,
                            "issue_name": disease_key,
                            "category": data.get("category", "unknown"),
                            **product
                        }
                    })

    # Return up to n_results
    return results[:n_results]

def rag_health_check() -> dict:
    """Mock health check since DB is now in-memory."""
    return {
        "status": "ok",
        "doc_count": sum(len(d) for d in MEDICINE_DB.values()),
        "model": "in-memory-dict"
    }