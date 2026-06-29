from datetime import datetime, timezone
import uuid
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID, SQLAlchemyBaseOAuthAccountTableUUID
from database import Base

class OAuthAccount(SQLAlchemyBaseOAuthAccountTableUUID, Base):
    pass

class User(SQLAlchemyBaseUserTableUUID, Base):
    oauth_accounts: Mapped[list[OAuthAccount]] = relationship( "OAuthAccount", lazy="joined")
    sessions: Mapped[list["Session"]] = relationship(back_populates="user")
    saved_supplements: Mapped[list["SavedSupplement"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"))
    questionnaire: Mapped[dict] = mapped_column(JSON)
    gap_pack: Mapped[list] = mapped_column(JSON, default=list)
    symptom_pack: Mapped[list] = mapped_column(JSON, default=list)
    goal_pack: Mapped[list] = mapped_column(JSON, default=list)
    safety_warnings: Mapped[list] = mapped_column(JSON, default=list)
    narrative: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(back_populates="session")
    saved_supplements: Mapped[list["SavedSupplement"]] = relationship(back_populates="session")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    role: Mapped[str] = mapped_column(String)
    content: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session: Mapped["Session"] = relationship(back_populates="messages")


class SavedSupplement(Base):
    __tablename__ = "saved_supplements"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user.id"))
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    name: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship(back_populates="saved_supplements")
    session: Mapped["Session"] = relationship(back_populates="saved_supplements")