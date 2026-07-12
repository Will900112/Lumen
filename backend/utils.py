import os
import re
import threading

import cohere
import openai
from dotenv import load_dotenv
from pinecone import Pinecone
from rank_bm25 import BM25Okapi

from config import EMBEDDING_MODEL, RERANKER_MODEL

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
        model=RERANKER_MODEL,
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


_bm25_cache = {}
_bm25_lock = threading.Lock()

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

def _iter_id_batches(index, batch_size: int = 100):
    """Normalize index.list() output across Pinecone SDK versions:
    some yield ListResponse pages, others yield bare id strings."""
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

def _fetch_all_docs(collection_name: str) -> list[str]:
    index = _pc.Index(PINECONE_INDEX[collection_name])
    docs = []
    for ids in _iter_id_batches(index):
        if not ids:
            continue
        res = index.fetch(ids=ids)
        docs.extend(v.metadata.get("document", "") for v in res.vectors.values())
    return docs

def _get_bm25(collection_name: str):
    # Lock so concurrent callers (agent3 runs retrieval in a thread pool)
    # don't each fetch the whole index when the cache is cold.
    if collection_name not in _bm25_cache:
        with _bm25_lock:
            if collection_name not in _bm25_cache:
                docs = _fetch_all_docs(collection_name)
                bm25 = BM25Okapi([_tokenize(d) for d in docs])
                _bm25_cache[collection_name] = (bm25, docs)
    return _bm25_cache[collection_name]

def bm25_query(collection_name: str, query_text: str, n_results: int = 20) -> list[str]:
    bm25, docs = _get_bm25(collection_name)
    scores = bm25.get_scores(_tokenize(query_text))       
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return [docs[i] for i in ranked[:n_results]]          

def build_bm25_indexes(collection_names: list[str]) -> None:
    for name in collection_names:
        _get_bm25(name)