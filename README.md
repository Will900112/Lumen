# Lumen — AI Supplement Advisor

![CI](https://github.com/Will900112/Lumen/actions/workflows/ci.yml/badge.svg)

**Live demo:** [lumen-one-iota.vercel.app](https://lumen-one-iota.vercel.app)

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

Create `backend/.env`:

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
