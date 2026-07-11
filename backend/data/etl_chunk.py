"""ETL step 2: chunk parsed Markdown, embed with OpenAI, upsert to Pinecone.

Input:  backend/data/parsed/<book>.md
Output: Pinecone serverless indexes (one per knowledge layer)

Chunk text is stored in vector metadata under "document" — the same shape
`utils.pinecone_query` reads at query time. Re-running is idempotent:
chunk IDs are deterministic, so existing vectors are overwritten in place.
"""

import os
import re
import time

import openai
from dotenv import load_dotenv
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

DATA_DIR = os.path.dirname(__file__)
PARSED_DIR = os.path.join(DATA_DIR, "parsed")

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536
CHUNK_SIZE = 600      # words per chunk
CHUNK_OVERLAP = 100   # words carried over between chunks
MIN_CHUNK_CHARS = 50  # drop fragments shorter than this
BATCH_SIZE = 100      # embeddings per OpenAI call / vectors per upsert

# parsed markdown filename -> Pinecone index
BOOKS = {
    "modern_nutrition.md": "lumen-gap",
    "nutritional_medicine.md": "lumen-clinical",
    "stockleys_interactions.md": "lumen-interactions",
}

openai_client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


def clean_text(text: str) -> str:
    text = re.sub(r"#\s+CHAPTER\s+[\d\|]+\s*\*[^\n]*\n", "", text)
    text = re.sub(r"#\s+PART\s+\d+\s*\*[^\n]*\n", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_into_chunks(text: str) -> list[str]:
    chunks = []
    words = text.split()
    current_chunk: list[str] = []

    for word in words:
        current_chunk.append(word)
        if len(current_chunk) >= CHUNK_SIZE:
            chunks.append(" ".join(current_chunk))
            current_chunk = current_chunk[-CHUNK_OVERLAP:]

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return [c for c in chunks if len(c.strip()) >= MIN_CHUNK_CHARS]


def embed_batch(texts: list[str]) -> list[list[float]]:
    response = openai_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]


def ensure_index(name: str) -> None:
    if name not in [i.name for i in pc.list_indexes()]:
        print(f"[create] index {name}")
        pc.create_index(
            name=name,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        while not pc.describe_index(name).status["ready"]:
            time.sleep(1)


def process_book(md_name: str, index_name: str) -> None:
    md_path = os.path.join(PARSED_DIR, md_name)
    if not os.path.exists(md_path):
        print(f"[skip] parsed file not found: {md_name}")
        return

    with open(md_path, "r", encoding="utf-8") as f:
        chunks = split_into_chunks(clean_text(f.read()))

    print(f"[chunk] {md_name}: {len(chunks)} chunks -> {index_name}")
    ensure_index(index_name)
    index = pc.Index(index_name)

    for start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[start:start + BATCH_SIZE]
        embeddings = embed_batch(batch)
        index.upsert(vectors=[
            {
                "id": f"chunk_{start + i}",
                "values": embeddings[i],
                "metadata": {"document": batch[i], "chunk_index": start + i},
            }
            for i in range(len(batch))
        ])
        print(f"  upserted {min(start + BATCH_SIZE, len(chunks))}/{len(chunks)}")


def main() -> None:
    for md_name, index_name in BOOKS.items():
        process_book(md_name, index_name)
    print("[done] all books processed")


if __name__ == "__main__":
    main()
