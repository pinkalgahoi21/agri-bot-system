"""Persistent semantic retrieval over the bundled agricultural reference PDFs."""
import logging
import os
import re
from functools import lru_cache
from pathlib import Path

from database.medicine import normalize_disease

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
    collection = store.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    stale = set(collection.get(include=[])["ids"])
    batch = []
    try:
        for record in chunks(KNOWLEDGE):
            stale.discard(record[0])
            batch.append(record)
            if len(batch) == 32:
                insert(collection, batch)
                batch.clear()
        if batch:
            insert(collection, batch)
        if stale:
            collection.delete(ids=list(stale))
        if not collection.count():
            raise ValueError("No PDF passages indexed")
        print(f"Indexed {collection.count()} passages")
    except Exception:
        raise


def insert(collection, batch):
    ids, documents, metadata = zip(*batch)
    collection.upsert(ids=list(ids), documents=list(documents), metadatas=list(metadata))


@lru_cache(maxsize=1)
def index():
    return client().get_collection(COLLECTION)


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
    result = db.query(query_texts=[f"{crop} {disease} crop disease treatment"], n_results=min(count, 48))
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
