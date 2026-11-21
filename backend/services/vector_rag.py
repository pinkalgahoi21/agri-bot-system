"""Persistent semantic retrieval over the bundled agricultural reference PDFs."""
import base64
import gzip
import hashlib
import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path

from database.medicine import normalize_disease
from app.core.embeddings import get_embeddings, metadata, verify_collection

ROOT = Path(__file__).resolve().parents[2]
COLLECTION = "agri_pdf_minilm_v1"
KNOWLEDGE = ROOT / "data" / "knowledge"


def chunks(directory):
    from pypdf import PdfReader

    for path in sorted(directory.iterdir()):
        if path.suffix.lower() in {".md", ".txt", ".csv", ".docx"}:
            if path.suffix.lower() == ".docx":
                from zipfile import ZipFile
                from xml.etree import ElementTree
                with ZipFile(path) as archive:
                    xml = ElementTree.fromstring(archive.read("word/document.xml"))
                content = " ".join(node.text or "" for node in xml.iter() if node.tag.endswith("}t"))
            else:
                content = path.read_text(encoding="utf-8-sig")
            for offset in range(0, len(content), 800):
                passage = content[offset:offset + 1000].strip()
                if passage:
                    yield f"{path.name}:section:{offset}", passage, {"source": path.name, "page": 0}
            continue
        if path.suffix.lower() != ".pdf":
            continue
        count = 0
        for page, item in enumerate(PdfReader(path).pages, 1):
            lines = (item.extract_text() or "").splitlines()
            for offset in range(0, len(lines), 16):
                passage = "\n".join(lines[offset:offset + 20]).strip()
                if len(passage) >= 40:
                    count += 1
                    yield f"{path.name}:{page}:{offset}", passage, {"source": path.name, "page": page}
        if not count:
            raise ValueError(f"No searchable text in {path.name}")


def client():
    import chromadb
    return chromadb.PersistentClient(path=os.getenv("VECTOR_DB_DIR", str(ROOT / "vector_index")))


def build(reset=False):
    store = client()
    if reset and COLLECTION in [entry.name for entry in store.list_collections()]:
        store.delete_collection(COLLECTION)
    if COLLECTION in [entry.name for entry in store.list_collections()]:
        collection = store.get_collection(COLLECTION)
        verify_collection(collection)
    else:
        collection = store.create_collection(COLLECTION, metadata={"hnsw:space": "cosine", **metadata()})
    existing = collection.get(include=["documents"])
    stored = dict(zip(existing["ids"], existing["documents"]))
    stale = set(stored)
    marker = readiness_file()
    marker.unlink(missing_ok=True)
    index.cache_clear()
    batch = []
    for record in chunks(KNOWLEDGE):
        stale.discard(record[0])
        if stored.get(record[0]) == record[1]:
            continue
        batch.append(record)
        if len(batch) == 32:
            insert(collection, batch)
            batch.clear()
    if batch:
        insert(collection, batch)
    if stale:
        collection.delete(ids=list(stale))
    count = collection.count()
    if not count:
        raise ValueError("No passages indexed")
    pending = marker.with_suffix(".tmp")
    pending.write_text(json.dumps(signature(collection)), encoding="utf-8")
    pending.replace(marker)
    print(f"Indexed {count} passages")


def readiness_file():
    return Path(os.getenv("VECTOR_DB_DIR", str(ROOT / "vector_index"))) / "agri-ready.json"


def corpus_hash():
    digest = hashlib.sha256()
    for path in sorted(KNOWLEDGE.iterdir()):
        if path.suffix.lower() in {".pdf", ".txt", ".md", ".csv", ".docx"}:
            digest.update(path.name.encode())
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def signature(collection):
    return {**metadata(), "collection": str(collection.id), "count": collection.count(), "documents": corpus_hash()}


def ensure_index():
    if COLLECTION in [entry.name for entry in client().list_collections()]:
        try:
            return index()
        except IncompleteIndex:
            pass
    if not restore_seed():
        build()
    return index()


SEED = ROOT / "data" / "reference-index.jsonl.gz"


def export_seed():
    import numpy as np
    db = index()
    pending = SEED.with_suffix(".tmp")
    with gzip.open(pending, "wt", encoding="utf-8") as stream:
        header = {**metadata(), "documents": corpus_hash(), "count": db.count()}
        stream.write(json.dumps(header) + "\n")
        for offset in range(0, db.count(), 32):
            batch = db.get(limit=32, offset=offset, include=["documents", "metadatas", "embeddings"])
            for key, doc, meta, vector in zip(batch["ids"], batch["documents"], batch["metadatas"], batch["embeddings"]):
                encoded = base64.b64encode(np.asarray(vector, dtype="<f4").tobytes()).decode("ascii")
                stream.write(json.dumps([key, doc, meta, encoded]) + "\n")
    pending.replace(SEED)


def restore_seed():
    import numpy as np
    if not SEED.exists():
        return False
    with gzip.open(SEED, "rt", encoding="utf-8") as stream:
        header = json.loads(next(stream))
        if any(header.get(k) != v for k, v in {**metadata(), "documents": corpus_hash()}.items()):
            return False
        db = client().get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine", **metadata()})
        verify_collection(db)
        marker = readiness_file()
        marker.unlink(missing_ok=True)
        stale = set(db.get(include=[])["ids"])
        from itertools import islice
        while lines := list(islice(stream, 32)):
            ids, docs, metas, encoded = zip(*(json.loads(line) for line in lines))
            vectors = [np.frombuffer(base64.b64decode(item), dtype="<f4").tolist() for item in encoded]
            db.upsert(ids=list(ids), documents=list(docs), metadatas=list(metas), embeddings=vectors)
            stale.difference_update(ids)
        if stale:
            db.delete(ids=list(stale))
        if db.count() != header["count"] or not db.count():
            raise IncompleteIndex("Bundled reference index is incomplete")
        pending = marker.with_suffix(".tmp")
        pending.write_text(json.dumps(signature(db)), encoding="utf-8")
        pending.replace(marker)
    return True


class IncompleteIndex(RuntimeError):
    pass


def insert(collection, batch):
    ids, documents, metadata = zip(*batch)
    for attempt in range(4):
        try:
            vectors = get_embeddings().embed_documents(list(documents))
            break
        except Exception as exc:
            if "429" not in str(exc) or attempt == 3 or "perday" in str(exc).lower():
                raise
            time.sleep(65)
    collection.upsert(ids=list(ids), documents=list(documents), metadatas=list(metadata), embeddings=vectors)


@lru_cache(maxsize=1)
def index():
    collection = client().get_collection(COLLECTION)
    verify_collection(collection)
    try:
        recorded = json.loads(readiness_file().read_text(encoding='utf-8'))
    except (FileNotFoundError, ValueError):
        recorded = None
    if not recorded or recorded != signature(collection) or not collection.count():
        raise IncompleteIndex('Reference index needs a complete build')
    return collection


def mentions(text, phrase):
    return bool(phrase and re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text))


@lru_cache(maxsize=32)
def table_page(source, page):
    from pypdf import PdfReader
    directory = KNOWLEDGE.resolve()
    path = (directory / source).resolve()
    if path.parent != directory or path.suffix.lower() != ".pdf" or page < 1:
        return ""
    with path.open("rb") as handle:
        layout = PdfReader(handle).pages[page - 1].extract_text(extraction_mode="layout")
    return "\n".join(line.rstrip() for line in layout.splitlines() if line.strip())


def search_pdf(disease, crop, limit=3):
    crop = crop.strip().lower()
    disease = disease.strip().lower()
    if not crop or not disease or limit <= 0:
        return []
    crops = {"rice": ("rice", "paddy"), "maize": ("maize", "corn")}
    names = next((group for group in crops.values() if crop in group), (crop,))
    issues = {disease, normalize_disease(disease)}
    db = index()
    count = db.count()
    if not count:
        return []
    result = db.query(query_embeddings=[get_embeddings().embed_query(f"{crop} {disease} crop disease treatment")], n_results=min(count, 48))
    hits = []
    for passage, metadata, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0]):
        if distance > float(os.getenv("RAG_MAX_DISTANCE", "0.85")):
            continue
        text = " ".join(passage.lower().split())
        if any(mentions(text, name) for name in names) and any(mentions(text, issue) for issue in issues):
            hits.append({"document": passage, "metadata": metadata})
            if len(hits) >= limit:
                break
    return hits


if __name__ == "__main__":
    build()
