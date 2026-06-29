import os
import time
import jwt
import secrets
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

load_dotenv()

from pipeline import run, chat, PipelineError
from state import AgentSharedState, SupplementRecommendation
from database import engine, get_async_session, Base
from model import User, Session as DBSession, Message, SavedSupplement
from auth import (
    auth_backend,
    fastapi_users,
    current_active_user,
    google_oauth_client ,
    UserCreate,
    UserRead,
    UserUpdate,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(lifespan=lifespan)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", FRONTEND_URL).split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth
SECRET = os.getenv("SECRET_KEY")

from auth import get_user_manager

OAUTH_CALLBACK_URL = os.getenv("OAUTH_CALLBACK_URL", "http://localhost:8000/auth/google/callback")
STATE_LIFETIME_SECONDS = 10 * 60


def _generate_state() -> str:
    """Issue a short-lived state JWT to prevent CSRF in the OAuth flow."""
    payload = {
        "csrf": secrets.token_urlsafe(32),
        "exp": int(time.time()) + STATE_LIFETIME_SECONDS,
        "aud": "lumen:oauth-state",
    }
    return jwt.encode(payload, SECRET, algorithm="HS256")


def _verify_state(state: str) -> None:
    """Verify the state JWT; raise 400 if invalid or expired."""
    try:
        jwt.decode(state, SECRET, audience="lumen:oauth-state", algorithms=["HS256"])
    except jwt.PyJWTError:
        raise HTTPException(400, "Invalid or expired state token")


# Custom Google OAuth endpoints
@app.get("/auth/google/authorize")
async def google_oauth_authorize():
    state = _generate_state()
    authorization_url = await google_oauth_client.get_authorization_url(
        OAUTH_CALLBACK_URL,
        state=state,
        scope=["email", "profile"],
    )
    return {"authorization_url": authorization_url}


@app.get("/auth/google/callback")
async def google_oauth_callback(
    code: str,
    state: str,
    user_manager=Depends(get_user_manager),
):
    _verify_state(state)

    token = await google_oauth_client.get_access_token(code, OAUTH_CALLBACK_URL)
    account_id, account_email = await google_oauth_client.get_id_email(
        token["access_token"]
    )

    if not account_email:
        raise HTTPException(400, "Google did not return an email")

    try:
        user = await user_manager.oauth_callback(
            "google",
            token["access_token"],
            account_id,
            account_email,
            token.get("expires_at"),
            token.get("refresh_token"),
            associate_by_email=True,
            is_verified_by_default=True,
        )
    except Exception as e:
        raise HTTPException(400, f"OAuth user creation failed: {e}")

    strategy = auth_backend.get_strategy()
    jwt_token = await strategy.write_token(user)

    return RedirectResponse(
        f"{FRONTEND_URL}/auth/google/callback#token={jwt_token}",
        status_code=302,
    )

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)


# Request schemas
class RecommendRequest(BaseModel):
    questionnaire: dict

class ChatRequest(BaseModel):
    session_id: str
    message: str

class SaveSupplementRequest(BaseModel):
    session_id: str
    name: str


# Recommendation
@app.post("/recommend")
async def recommend(
    req: RecommendRequest,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        state = await run(req.questionnaire)
    except PipelineError as e:
        raise HTTPException(status_code=502, detail={"step": e.step, "message": str(e)})

    new_session = DBSession(
        user_id=user.id,
        questionnaire=req.questionnaire,
        gap_pack=[r.model_dump() for r in state.gap_pack],
        symptom_pack=[r.model_dump() for r in state.symptom_pack],
        goal_pack=[r.model_dump() for r in state.goal_pack],
        safety_warnings=state.safety_warnings,
        narrative=state.narrative_report,
    )
    db.add(new_session)
    await db.commit()
    await db.refresh(new_session)

    return {
        "session_id": new_session.id,
        "gap_pack":      new_session.gap_pack,
        "symptom_pack":  new_session.symptom_pack,
        "goal_pack":     new_session.goal_pack,
        "safety_warnings": new_session.safety_warnings,
        "narrative":     new_session.narrative,
    }


# Chat
async def _load_session_state(session_id: str, user: User, db: AsyncSession):
    """Rebuild an AgentSharedState from a persisted DB session."""
    result = await db.execute(
        select(DBSession).where(
            DBSession.id == session_id,
            DBSession.user_id == user.id,
        )
    )
    db_session = result.scalar_one_or_none()
    if db_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    def to_recs(items):
        return [SupplementRecommendation(**i) for i in items]

    state = AgentSharedState(raw_questionnaire=db_session.questionnaire)
    state.gap_pack         = to_recs(db_session.gap_pack)
    state.symptom_pack     = to_recs(db_session.symptom_pack)
    state.goal_pack        = to_recs(db_session.goal_pack)
    state.safety_warnings  = db_session.safety_warnings
    state.narrative_report = db_session.narrative
    return state


@app.post("/chat")
async def chat_endpoint(
    req: ChatRequest,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    state = await _load_session_state(req.session_id, user, db)

    result = await db.execute(
        select(Message)
        .where(Message.session_id == req.session_id)
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()
    history = [{"role": m.role, "content": m.content} for m in messages]

    try:
        reply, _ = await chat(state, history, req.message)
    except PipelineError as e:
        raise HTTPException(status_code=502, detail={"step": e.step, "message": str(e)})

    db.add(Message(session_id=req.session_id, role="user",      content=req.message))
    db.add(Message(session_id=req.session_id, role="assistant", content=reply))
    await db.commit()

    return {"reply": reply}


# Sessions
@app.get("/sessions")
async def list_sessions(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        select(DBSession)
        .where(DBSession.user_id == user.id)
        .order_by(DBSession.created_at.desc())
    )
    sessions = result.scalars().all()
    return [
        {"id": s.id, "created_at": s.created_at, "narrative": s.narrative[:100]}
        for s in sessions
    ]


@app.get("/sessions/{session_id}")
async def get_session(
    session_id: str,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        select(DBSession).where(
            DBSession.id == session_id,
            DBSession.user_id == user.id,
        )
    )
    s = result.scalar_one_or_none()
    if s is None:
        raise HTTPException(status_code=404, detail="Session not found")

    msg_result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at)
    )
    messages = msg_result.scalars().all()

    return {
        "id": s.id,
        "created_at": s.created_at,
        "gap_pack": s.gap_pack,
        "symptom_pack": s.symptom_pack,
        "goal_pack": s.goal_pack,
        "safety_warnings": s.safety_warnings,
        "narrative": s.narrative,
        "messages": [
            {"role": m.role, "content": m.content, "created_at": m.created_at}
            for m in messages
        ],
    }


# Saved supplements
@app.post("/list/add")
async def save_supplement(
    req: SaveSupplementRequest,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        select(SavedSupplement).where(
            SavedSupplement.user_id == user.id,
            SavedSupplement.name == req.name,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        return {"id": existing.id, "name": existing.name, "already_existed": True}

    saved = SavedSupplement(
        user_id=user.id,
        session_id=req.session_id,
        name=req.name,
    )
    db.add(saved)
    await db.commit()
    await db.refresh(saved)
    return {"id": saved.id, "name": saved.name}


@app.get("/list")
async def get_saved_list(
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        select(SavedSupplement)
        .where(SavedSupplement.user_id == user.id)
        .order_by(SavedSupplement.created_at.desc())
    )
    items = result.scalars().all()
    return [
        {"id": i.id, "name": i.name, "session_id": i.session_id, "created_at": i.created_at}
        for i in items
    ]


@app.delete("/list/{item_id}")
async def delete_saved(
    item_id: str,
    user: User = Depends(current_active_user),
    db: AsyncSession = Depends(get_async_session),
):
    result = await db.execute(
        select(SavedSupplement).where(
            SavedSupplement.id == item_id,
            SavedSupplement.user_id == user.id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(item)
    await db.commit()
    return {"ok": True}
