# Lumen — AI Supplement Advisor

![CI](https://github.com/Will900112/Lumen/actions/workflows/ci.yml/badge.svg)

**Live demo:** [lumen-one-iota.vercel.app](https://lumen-one-iota.vercel.app)
*(first request may take ~30s — free-tier backend cold start)*

Personalized supplement recommendations powered by a multi-agent RAG pipeline.
Lumen analyzes a user's diet, lifestyle, symptoms, and goals to recommend
evidence-backed supplements, with herb–drug interaction checks against the
user's medications and conditions.

---

## Features

- **Questionnaire-driven recommendations** — diet, lifestyle, symptoms, goals
- **4-agent reasoning pipeline** — profile analysis → clinical proposal → RAG grounding → safety report
- **Evidence-backed** — every recommendation is grounded in textbook chunks retrieved from a vector DB and reranked
- **Safety-aware** — drug-supplement interaction screening before final recommendation
- **Conversational follow-up** — per-session chat to ask "why this" or "is it safe with X"
- **Saved list** — bookmark supplements across sessions
- **Auth** — email/password + Google OAuth

---

## Tech Stack

**Frontend**
- Next.js 15 (App Router) + TypeScript
- Tailwind CSS + shadcn/ui
- Vercel deployment

**Backend**
- FastAPI (async)
- PostgreSQL via SQLAlchemy + asyncpg (Supabase)
- fastapi-users for auth, httpx-oauth for Google OAuth
- Render deployment

**AI / RAG**
- OpenAI `gpt-4o-mini` for reasoning, `text-embedding-3-small` for embeddings
- Pinecone (serverless) for vector storage
- Cohere `rerank-v3.5` for relevance reranking

---

## Architecture

```
User questionnaire
       │
       ▼
┌────────────────────┐
│ Agent 1            │  Profile analyzer
│ profile_analyzer   │  → gap candidates, symptom tags, safety profile
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Agent 2            │  Clinical proposer
│ clinical_proposer  │  → symptom + goal candidates
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Agent 3            │  RAG grounder
│ rag_grounder       │  → Pinecone retrieve + Cohere rerank → evidence scores
└─────────┬──────────┘
          ▼
┌────────────────────┐
│ Agent 4            │  Safety report
│ safety_report      │  → interaction RAG + final ranked packs + warnings
└─────────┬──────────┘
          ▼
   Three packs (gap / symptom / goal) + safety warnings + narrative
```

Agent 5 (`agent5_chat`) handles per-session follow-up conversation, given
the full state from the recommendation run.

---

## Project Structure

```
supplement-recommender/
├── backend/
│   ├── agents/                  # 5 specialized agents
│   ├── data/                    # ETL scripts + parsed textbooks
│   ├── eval/                    # Retrieval benchmark (build + run + results)
│   ├── tests/                   # pytest suite
│   ├── auth.py                  # fastapi-users + Google OAuth setup
│   ├── database.py              # async SQLAlchemy engine
│   ├── main.py                  # FastAPI app, routes, OAuth callbacks
│   ├── model.py                 # ORM models
│   ├── pipeline.py              # Agent orchestration + error wrapping
│   ├── state.py                 # Shared state schema
│   └── utils.py                 # Embeddings, Pinecone, Cohere helpers
└── frontend/
    └── src/
        ├── app/
        │   ├── (app)/           # Auth-gated layout group
        │   │   ├── questionnaire/
        │   │   ├── result/[sessionId]/
        │   │   └── list/
        │   ├── auth/google/callback/
        │   ├── login/
        │   └── register/
        ├── components/
        └── lib/api.ts           # Typed API client
```

---

## Setup (local)

### Prerequisites
- Python 3.11+
- Node.js 20+
- Accounts: OpenAI, Cohere, Pinecone, Supabase, Google Cloud (OAuth)

### Backend

```bash
cd backend
pip install -r requirements.txt
```

Create `backend/.env` (see `backend/.env.example`):

```env
# Required
OPENAI_API_KEY=sk-...
COHERE_API_KEY=...
PINECONE_API_KEY=...
DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:6543/postgres
SECRET_KEY=<random 64-char hex>

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...

# Optional (defaults shown)
FRONTEND_URL=http://localhost:3000
OAUTH_CALLBACK_URL=http://localhost:8000/auth/google/callback
# CORS_ORIGINS=https://prod.app,https://preview.app
```

Run:
```bash
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Run:
```bash
npm run dev
```

---

## Data Pipeline (one-time)

Source PDFs (clinical references) live in `backend/data/raw/` (gitignored).

1. **Parse** — `python data/etl_parse.py` converts all source PDFs to Markdown via LlamaParse
2. **Chunk** — `python data/etl_chunk.py` chunks each book, batch-embeds with OpenAI, and upserts to the matching Pinecone index

Both scripts are idempotent: parsed files are skipped if present, and chunk IDs
are deterministic so re-running overwrites in place.

---

## Testing

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Covers the ETL chunking logic, OAuth CSRF state validation (expiry, tampering,
wrong audience, forged signature), and auth guards on every user-facing
endpoint. CI runs the suite plus a frontend production build on every push.

---

## Retrieval Evaluation

Retrieval quality is measured with a purpose-built benchmark (`backend/eval/`)
rather than eyeballing outputs. The goal is to answer, with numbers, whether
the production retriever (dense + Cohere rerank) is actually the best choice.

The RAG layer has **three separate vector indexes**, each answering a different
question and queried by a different agent:

| Index | Retrieves | Query style (from agent) |
|---|---|---|
| **gap** | nutrient-deficiency evidence, from diet/lifestyle | cause → mechanism → deficiency |
| **clinical** | supplement efficacy for symptoms/goals | "[supplement] [verb] [outcome] in [condition]" |
| **interactions** | herb–drug interaction evidence | keyword stack (herb + drug + effect) |

Each is evaluated independently, since a gap query is never run against the
clinical index in production.

### How the benchmark is built

1. **Corpus snapshot** (`export_corpus.py`) — pull all 4,247 chunks from the
   production Pinecone indexes, so the benchmark measures exactly what the app
   retrieves.
2. **Synthetic query generation** (`generate_eval_set.py`) — for each of the
   three indexes, an LLM (`gpt-5.6-terra`) reverse-generates a query from a
   sampled chunk, in the *same style the corresponding agent uses in
   production* (gap = "cause → mechanism → deficiency" phrasing, clinical =
   "[supplement] [verb] [outcome] in [condition]", interactions = keyword
   stack). A realism constraint keeps queries inside the questionnaire's actual
   input space (e.g. a deficiency cause must be inferable from diet/lifestyle
   fields, not from pregnancy or a medical procedure).
3. **Independent verification** (`verify_gold.py`) — a separate scoring pass
   (1–5) confirms each gold chunk genuinely answers its query; this is what
   caught (and filtered) chunks that were mostly reference lists.
4. **Balancing** (`prune_eval_set.py`) — randomly downsampled to **60 queries
   per index (180 total)**. Random, not top-scored, so the grader model's
   preference is not baked in.

Each query is scored only against its own index (gap queries hit `lumen-gap`,
etc.). Gold is a single chunk id, so **Recall@k** = "was the gold chunk in the
top k" and **MRR@10** = how highly it ranked.

### Results (180 queries, 60 per index)

**Macro-average across indexes** (equal weight per index):

| Variant | Recall@5 | Recall@20 | MRR@10 |
|---|---|---|---|
| dense | 0.789 | 0.922 | 0.569 |
| bm25 | 0.822 | 0.967 | 0.662 |
| hybrid (RRF) | 0.839 | 0.961 | 0.637 |
| dense + rerank *(current prod)* | 0.911 | 0.961 | 0.732 |
| **bm25 + rerank** | **0.928** | 0.978 | **0.743** |
| hybrid + rerank | 0.922 | **0.983** | 0.740 |

**Per-index breakdown** (R@5 / R@20 / MRR@10):

| Variant | gap R@5 | gap R@20 | gap MRR | clin R@5 | clin R@20 | clin MRR | int R@5 | int R@20 | int MRR |
|---|---|---|---|---|---|---|---|---|---|
| dense | 0.550 | 0.833 | 0.333 | 0.933 | 0.967 | 0.664 | 0.883 | 0.967 | 0.709 |
| bm25 | 0.683 | 0.933 | 0.493 | 0.817 | 0.967 | 0.633 | 0.967 | 1.000 | 0.858 |
| hybrid | 0.683 | 0.917 | 0.450 | 0.883 | 0.983 | 0.685 | 0.950 | 0.983 | 0.776 |
| dense + rerank | 0.767 | 0.917 | 0.508 | 0.983 | 0.983 | 0.817 | 0.983 | 0.983 | 0.871 |
| bm25 + rerank | 0.817 | 0.950 | 0.532 | 0.967 | 0.983 | 0.817 | 1.000 | 1.000 | 0.879 |
| hybrid + rerank | 0.800 | 0.967 | 0.524 | 0.967 | 0.983 | 0.817 | 1.000 | 1.000 | 0.879 |

### Findings

- **Reranking is the dominant lever.** Adding Cohere `rerank-v3.5` lifts
  Recall@5 by ~10 points regardless of first stage; the spread *between* first
  stages (dense vs bm25 vs hybrid) is only ~1.5 points. Rerank earns its place;
  hybrid fusion does not justify its added complexity over reranking alone.
- **BM25 beats dense on this corpus.** Medical terminology is precise, so exact
  keyword matching (bm25, 0.822) outperforms pure semantic search (dense,
  0.789). `bm25 + rerank` is the top configuration overall and reaches perfect
  Recall@5 on the interactions index (drug/herb names are exact tokens).
- **The gap layer is the hardest** (best R@5 ≈ 0.82). Its queries encode a
  lifestyle *cause* ("vegan diet…") that never appears in the textbook chunk,
  so semantic similarity is diluted — a concrete, measured direction for future
  work (heading-aware chunking, or a larger embedding model).
- **The best first stage differs by index.** BM25 wins on gap (0.767 → 0.817
  R@5) and interactions (perfect 1.000), where exact nutrient/drug tokens
  dominate; but **dense wins on clinical** (0.983 vs 0.967), where efficacy is
  described semantically ("improves sleep quality"). A per-layer retrieval
  strategy could squeeze out the best of each — though the clinical gap is a
  single query, so likely within noise. `hybrid + rerank` was statistically
  tied with `bm25 + rerank` and does not justify its extra complexity.

### From evaluation to production

The benchmark drove one change: the **interactions** safety lookup (Agent 4)
was switched from dense to its best configuration, **BM25 + rerank**. BM25 is
built in memory at startup from the Pinecone corpus, so it stays in sync with
the vector store.

**gap** showed a similar BM25 lean but wasn't migrated — the gain is modest and
its retrieval sits inside Agent 3's parallel loop, so it's left as a scoped next
step rather than a riskier refactor for a small win. **clinical** stays on dense
(the one index where dense wins), which also avoids loading a BM25 index it
doesn't need — memory headroom matters on the free-tier backend.

### Caveats

- **Single positive label** — only the source chunk is marked correct, so
  Recall is under-counted when other chunks also answer a query. The bias is
  identical across variants, so their *relative* ranking is valid.
- **Same-model generation and verification** — both use `gpt-5.6-terra`;
  cross-model verification (e.g. Claude) would be a stronger check.

Reproduce with `export_corpus.py → generate_eval_set.py → verify_gold.py →
prune_eval_set.py → run_retrieval.py`.

---

## Deployment

| Component | Platform | Notes |
|-----------|----------|-------|
| Frontend  | Vercel   | Set `NEXT_PUBLIC_API_URL` to the Render URL |
| Backend   | Render   | Set all `.env` vars in dashboard; use Supabase Transaction Pooler |
| Database  | Supabase | Free tier (Transaction Pooler, port 6543) |
| Vectors   | Pinecone | Free serverless tier (us-east-1) |

After deploying, update the Google OAuth authorized redirect URI to:
```
https://<your-backend>.onrender.com/auth/google/callback
```

---

## License

Private project — not yet licensed for redistribution.
