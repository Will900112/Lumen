import os
import re
import chromadb
import openai
from dotenv import load_dotenv

load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(
    path=os.path.join(os.path.dirname(__file__), "chroma")
)

CHUNK_SIZE = 600
CHUNK_OVERLAP = 100

def clean_text(text: str) -> str:
    text = re.sub(r'#\s+CHAPTER\s+[\d\|]+\s*\*[^\n]*\n', '', text)
    text = re.sub(r'#\s+PART\s+\d+\s*\*[^\n]*\n', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def split_into_chunks(text: str) -> list:
    chunks = []
    words = text.split()
    current_chunk = []
    current_size = 0

    for word in words:
        current_chunk.append(word)
        current_size += 1

        if current_size >= CHUNK_SIZE:
            chunks.append(" ".join(current_chunk))
            current_chunk = current_chunk[-CHUNK_OVERLAP:]
            current_size = len(current_chunk)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def get_embedding(text: str) -> list:
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def process():
    md_path = os.path.join(os.path.dirname(__file__), "parsed", "stockleys_interactions.md")
    with open(md_path, "r", encoding="utf-8") as f:
        full_text = f.read()

    collection = chroma_client.get_or_create_collection("collection_interactions")

    full_text = clean_text(full_text)
    chunks = split_into_chunks(full_text)

    print(f"總共切成 {len(chunks)} 個 chunks")

    for i, chunk in enumerate(chunks):
        if len(chunk.strip()) < 50:
            continue

        embedding = get_embedding(chunk)

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[f"chunk_{i}"],
            metadatas=[{"chunk_index": i}]
        )

        if i % 50 == 0:
            print(f"  進度: {i}/{len(chunks)}")

    print(f"✅ 完成！")

if __name__ == "__main__":
    process()