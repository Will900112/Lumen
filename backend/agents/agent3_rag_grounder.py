import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from state import AgentSharedState, SupplementCandidate
from utils import get_embeddings_batch, rerank_with_cohere, pinecone_query, bm25_query

EVIDENCE_THRESHOLD = None

LAYER_COLLECTION = {
    "gap":     "collection_gap",
    "symptom": "collection_clinical",
    "goal":    "collection_clinical",
}
BM25_COLLECTIONS = {"collection_gap"}   


async def _process_candidate(candidate: SupplementCandidate, chunks: list[str]) -> None:
    if not chunks:
        return

    scores = await rerank_with_cohere(candidate.query_context, chunks)
    if not scores:
        return

    best = int(np.argmax(scores))
    candidate.evidence_score = float(scores[best])
    candidate.evidence_snippet = chunks[best][:300]
    candidate.passed = True if EVIDENCE_THRESHOLD is None else candidate.evidence_score > EVIDENCE_THRESHOLD


async def run_agent3(state: AgentSharedState) -> AgentSharedState:
    all_candidates = (
        state.gap_candidates +
        state.symptom_candidates +
        state.goal_candidates
    )

    if not all_candidates:
        return state

    # Step 1: only dense candidates need embeddings; BM25 works on raw text
    dense_candidates = [
        c for c in all_candidates
        if LAYER_COLLECTION[c.layer] not in BM25_COLLECTIONS
    ]
    embeddings = {}
    if dense_candidates:
        vecs = await get_embeddings_batch([c.query_context for c in dense_candidates])
        embeddings = {id(c): v for c, v in zip(dense_candidates, vecs)}

    # Step 2: retrieve per candidate — BM25 for gap, dense (Pinecone) for the rest
    def _retrieve(cand: SupplementCandidate) -> list[str]:
        collection = LAYER_COLLECTION[cand.layer]
        if collection in BM25_COLLECTIONS:
            return bm25_query(collection, cand.query_context, n_results=20)
        return pinecone_query(collection, embeddings[id(cand)], n_results=20)

    def _query_all():
        with ThreadPoolExecutor(max_workers=8) as ex:
            return list(ex.map(_retrieve, all_candidates))

    all_chunks = await asyncio.to_thread(_query_all)

    # Step 3: rerank with Cohere in parallel (one API call per candidate)
    await asyncio.gather(*[
        _process_candidate(cand, chunks)
        for cand, chunks in zip(all_candidates, all_chunks)
    ])

    return state