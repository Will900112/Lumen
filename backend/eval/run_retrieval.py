"""Phase 1c: offline retrieval benchmark. Reads only; does not touch production.

Runs each query against its OWN index (gap queries -> lumen-gap, etc.) with
several retrieval variants and reports Recall@k / MRR@10, per index and as a
macro-average across indexes.

Variants (round 1 — all use the existing 1536-dim embeddings, no re-embedding):
  dense          : text-embedding-3-small vectors in Pinecone (cosine)
  bm25           : classic BM25 over the local corpus snapshot
  hybrid         : RRF fusion of dense + bm25
  dense+rerank   : dense candidates re-ordered by Cohere rerank-v3.5
                   (this is the current production configuration)
  bm25+rerank    : bm25 candidates re-ordered by Cohere rerank-v3.5
  hybrid+rerank  : hybrid candidates re-ordered by Cohere rerank-v3.5

A reranker can only reorder the candidates the first stage retrieved, so a
first stage with higher Recall@candidate_depth raises the reranker's ceiling —
that is why we test rerank on top of each first stage, not just dense.

Gold label is a single chunk id per query, so Recall@k = "was the gold in the
top k". This under-counts when other chunks also answer the query, but that
bias is identical across variants, so the ranking between variants is valid.
"""

import json
import os
import re
from collections import defaultdict

import cohere
import openai
from dotenv import load_dotenv
from pinecone import Pinecone
from rank_bm25 import BM25Okapi

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CORPUS_PATH = os.path.join(DATA_DIR, "corpus.jsonl")
EVAL_SET_PATH = os.path.join(DATA_DIR, "eval_set.jsonl")
RESULTS_PATH = os.path.join(DATA_DIR, "retrieval_results.json")

EMBEDDING_MODEL = "text-embedding-3-small"
RERANK_MODEL = "rerank-v3.5"
CANDIDATE_DEPTH = 50   # how many candidates each retriever returns / reranks
RRF_K = 60             # standard RRF constant
K_VALUES = [5, 20]
MRR_AT = 10

INDEX_ORDER = ["lumen-gap", "lumen-clinical", "lumen-interactions"]

# Variants whose scores already exist in retrieval_results.json are reused
# instead of recomputed (saves paid rerank calls). Set to an empty set to run
# everything from scratch.
SKIP_VARIANTS = {"dense", "bm25", "hybrid", "dense+rerank"}

_openai = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
_co = cohere.Client(api_key=os.getenv("COHERE_API_KEY"))
_pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


# ---- corpus + per-index BM25 -------------------------------------------------

def load_corpus_by_index() -> dict[str, dict]:
    """index_name -> {ids, docs, bm25}."""
    rows_by_index: dict[str, list[dict]] = defaultdict(list)
    with open(CORPUS_PATH, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            rows_by_index[r["index"]].append(r)

    built = {}
    for idx, rows in rows_by_index.items():
        ids = [r["id"] for r in rows]
        docs = {r["id"]: r["document"] for r in rows}
        bm25 = BM25Okapi([tokenize(r["document"]) for r in rows])
        built[idx] = {"ids": ids, "docs": docs, "bm25": bm25}
    return built


# ---- retrievers (each returns a ranked list of chunk ids) --------------------

def retrieve_dense(query_vec, index_name, depth) -> tuple[list[str], dict[str, str]]:
    res = _pc.Index(index_name).query(
        vector=query_vec, top_k=depth, include_metadata=True
    )
    ids, docs = [], {}
    for m in res["matches"]:
        ids.append(m["id"])
        docs[m["id"]] = (m.get("metadata") or {}).get("document", "")
    return ids, docs


def retrieve_bm25(query_text, corpus, depth) -> list[str]:
    scores = corpus["bm25"].get_scores(tokenize(query_text))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
    return [corpus["ids"][i] for i in ranked[:depth]]


def fuse_rrf(rankings: list[list[str]], depth) -> list[str]:
    score = defaultdict(float)
    for ranking in rankings:
        for rank, _id in enumerate(ranking):
            score[_id] += 1.0 / (RRF_K + rank + 1)
    return sorted(score, key=score.get, reverse=True)[:depth]


def rerank(query_text, cand_ids, id_to_doc, depth) -> list[str]:
    docs = [id_to_doc.get(i, "") for i in cand_ids]
    if not docs:
        return []
    res = _co.rerank(query=query_text, documents=docs,
                     model=RERANK_MODEL, top_n=min(depth, len(docs)))
    return [cand_ids[r.index] for r in res.results]


# ---- metrics -----------------------------------------------------------------

def recall_at_k(ranked_ids, gold_id, k) -> float:
    return 1.0 if gold_id in ranked_ids[:k] else 0.0


def mrr(ranked_ids, gold_id, k) -> float:
    for rank, _id in enumerate(ranked_ids[:k], start=1):
        if _id == gold_id:
            return 1.0 / rank
    return 0.0


# ---- main --------------------------------------------------------------------

def main() -> None:
    corpus = load_corpus_by_index()
    queries = [json.loads(l) for l in open(EVAL_SET_PATH, encoding="utf-8")]

    print(f"embedding {len(queries)} queries...")
    embs = _openai.embeddings.create(
        model=EMBEDDING_MODEL, input=[q["query"] for q in queries]
    )
    for q, e in zip(queries, embs.data):
        q["_vec"] = e.embedding

    variants = ["dense", "bm25", "hybrid",
                "dense+rerank", "bm25+rerank", "hybrid+rerank"]
    rerank_source = {"dense+rerank": "dense",
                     "bm25+rerank": "bm25",
                     "hybrid+rerank": "hybrid"}

    saved = {}
    if os.path.exists(RESULTS_PATH):
        saved = json.load(open(RESULTS_PATH, encoding="utf-8"))
    to_run = [v for v in variants if not (v in SKIP_VARIANTS and v in saved)]
    print(f"computing {to_run}; reusing saved {sorted(set(variants) - set(to_run))}")

    acc = {v: defaultdict(lambda: defaultdict(list)) for v in to_run}

    for n, q in enumerate(queries, 1):
        idx, gold = q["index"], q["gold_id"]
        id_to_doc = corpus[idx]["docs"]  # full map, covers any candidate list

        dense_ids, _ = retrieve_dense(q["_vec"], idx, CANDIDATE_DEPTH)
        bm25_ids = retrieve_bm25(q["query"], corpus[idx], CANDIDATE_DEPTH)
        hybrid_ids = fuse_rrf([dense_ids, bm25_ids], CANDIDATE_DEPTH)
        cand = {"dense": dense_ids, "bm25": bm25_ids, "hybrid": hybrid_ids}

        for v in to_run:
            if v in cand:
                ids = cand[v]
            else:  # rerank the corresponding first-stage candidates
                ids = rerank(q["query"], cand[rerank_source[v]], id_to_doc, CANDIDATE_DEPTH)
            for k in K_VALUES:
                acc[v][idx][f"recall@{k}"].append(recall_at_k(ids, gold, k))
            acc[v][idx][f"mrr@{MRR_AT}"].append(mrr(ids, gold, MRR_AT))

        if n % 20 == 0:
            print(f"  {n}/{len(queries)}")

    metrics = [f"recall@{k}" for k in K_VALUES] + [f"mrr@{MRR_AT}"]
    summary = dict(saved)  # start from reused results, overwrite computed ones
    for v in to_run:
        per_index = {}
        for idx in INDEX_ORDER:
            per_index[idx] = {m: sum(acc[v][idx][m]) / len(acc[v][idx][m])
                              for m in metrics}
        macro = {m: sum(per_index[i][m] for i in INDEX_ORDER) / len(INDEX_ORDER)
                 for m in metrics}
        summary[v] = {"per_index": per_index, "macro": macro}

    json.dump(summary, open(RESULTS_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    shown = [v for v in variants if v in summary]

    # ---- print macro-average table ----
    header = f"{'variant':<16}" + "".join(f"{m:>12}" for m in metrics)
    print("\n=== Macro-average across indexes ===")
    print(header)
    print("-" * len(header))
    for v in shown:
        row = summary[v]["macro"]
        print(f"{v:<16}" + "".join(f"{row[m]:>12.3f}" for m in metrics))

    print("\n=== Per-index recall@5 ===")
    print(f"{'variant':<16}" + "".join(f"{i.replace('lumen-',''):>14}" for i in INDEX_ORDER))
    for v in shown:
        pi = summary[v]["per_index"]
        print(f"{v:<16}" + "".join(f"{pi[i]['recall@5']:>14.3f}" for i in INDEX_ORDER))

    print(f"\n[done] full results -> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
