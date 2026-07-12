"""Phase 1a: snapshot the full Pinecone corpus to a local JSONL file.

The eval corpus must be exactly what production retrieval sees, so we pull
from Pinecone (source of truth) rather than re-chunking local files.

Output: eval/data/corpus.jsonl — one row per chunk:
    {"id": "chunk_42", "index": "lumen-gap", "document": "..."}
"""

import json
import os

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
OUTPUT_PATH = os.path.join(DATA_DIR, "corpus.jsonl")

INDEXES = ["lumen-gap", "lumen-clinical", "lumen-interactions"]
FETCH_BATCH = 100

pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


def iter_id_batches(index, batch_size: int = FETCH_BATCH):
    """Normalize index.list() output across SDK versions."""
    buffer: list[str] = []
    for item in index.list(limit=batch_size):
        if hasattr(item, "vectors"):  # ListResponse page
            yield [v.id for v in item.vectors]
        elif isinstance(item, str):
            buffer.append(item)
            if len(buffer) == batch_size:
                yield buffer
                buffer = []
        else:
            yield list(item)
    if buffer:
        yield buffer


def export_index(index_name: str) -> list[dict]:
    index = pc.Index(index_name)
    rows = []
    for id_batch in iter_id_batches(index):
        response = index.fetch(ids=id_batch)
        for _id, vector in response.vectors.items():
            metadata = vector.metadata or {}
            rows.append({
                "id": _id,
                "index": index_name,
                "document": metadata.get("document", ""),
            })
    # deterministic order: chunk_0, chunk_1, ...
    rows.sort(key=lambda r: int(r["id"].rsplit("_", 1)[-1]))
    print(f"[export] {index_name}: {len(rows)} chunks")
    return rows


def main() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    all_rows = []
    for index_name in INDEXES:
        all_rows.extend(export_index(index_name))

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for row in all_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"[done] {len(all_rows)} chunks -> {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
