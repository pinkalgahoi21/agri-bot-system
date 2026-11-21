from functools import lru_cache
from langchain.embeddings import init_embeddings
from app.core.config import settings


@lru_cache(maxsize=1)
def get_embeddings():
    return init_embeddings(settings.EMBEDDING_MODEL, provider=settings.EMBEDDING_PROVIDER,
                           **settings.credentials(settings.EMBEDDING_PROVIDER))


def metadata():
    return {"embedding_provider": settings.EMBEDDING_PROVIDER, "embedding_model": settings.EMBEDDING_MODEL}


def verify_collection(collection):
    if any((collection.metadata or {}).get(key) != value for key, value in metadata().items()):
        raise ValueError("Embedding model differs or is unrecorded. Re-ingest with scripts/ingest.py --reset.")
