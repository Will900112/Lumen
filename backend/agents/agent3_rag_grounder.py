import asyncio
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from state import AgentSharedState, SupplementCandidate
from utils import get_embeddings_batch, rerank_with_cohere, pinecone_query

EVIDENCE_THRESHOLD = None

LAYER_COLLECTION = {
    "gap":     "collection_gap",
    "symptom": "collection_clinical",
    "goal":    "collection_clinical",
}


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

    # Step 1: batch all embeddings in a single OpenAI call
    embeddings = await get_embeddings_batch([c.query_context for c in all_candidates])

    # Step 2: query Pinecone in parallel (sync SDK -> thread pool)
    def _query_pinecone():
        with ThreadPoolExecutor(max_workers=8) as ex:
            return list(ex.map(
                lambda ce: pinecone_query(LAYER_COLLECTION[ce[0].layer], ce[1], n_results=20),
                zip(all_candidates, embeddings)
            ))

    all_chunks = await asyncio.to_thread(_query_pinecone)

    # Step 3: rerank with Cohere in parallel (one API call per candidate)
    await asyncio.gather(*[
        _process_candidate(cand, chunks)
        for cand, chunks in zip(all_candidates, all_chunks)
    ])

    return state
