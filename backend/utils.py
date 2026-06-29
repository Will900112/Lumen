import os
import openai
from dotenv import load_dotenv
from config import EMBEDDING_MODEL
import cohere
from pinecone import Pinecone

load_dotenv()

_openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

co = cohere.AsyncClient(api_key=os.getenv("COHERE_API_KEY"))

_pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
PINECONE_INDEX = {
    "collection_gap":          "lumen-gap",
    "collection_clinical":     "lumen-clinical",
    "collection_interactions": "lumen-interactions",
}

def pinecone_query(collection_name: str, embedding: list, n_results: int = 20) -> list[str]:
    index = _pc.Index(PINECONE_INDEX[collection_name])
    res = index.query(vector=embedding, top_k=n_results, include_metadata=True)
    return [m["metadata"].get("document", "") for m in res["matches"]]

async def rerank_with_cohere(query: str, documents: list[str]) -> list[float]:
    if not documents:
        return []
    results = await co.rerank(
        query=query,
        documents=documents,
        model="rerank-v3.5",
        top_n=len(documents),
    )
    scores = [0.0] * len(documents)
    for r in results.results:
        scores[r.index] = r.relevance_score
    return scores

async def get_embedding(text: str) -> list:
    response = await _openai_client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return response.data[0].embedding

async def get_embeddings_batch(texts: list[str]) -> list[list]:
    response = await _openai_client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    return [item.embedding for item in response.data]
