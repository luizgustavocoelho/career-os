import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def uid() -> str:
    return str(uuid.uuid4())


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, index=True)


class Owned(Record):
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


class User(Record, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    name: Mapped[str] = mapped_column(String(160))


class SessionToken(Owned, Base):
    __tablename__ = "sessions"
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    csrf_token: Mapped[str] = mapped_column(String(100))
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)


class RateLimit(Base):
    __tablename__ = "rate_limits"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    count: Mapped[int] = mapped_column(Integer, default=0)
    reset_at: Mapped[datetime] = mapped_column(DateTime)


class Profile(Owned, Base):
    __tablename__ = "profiles"
    __table_args__ = (UniqueConstraint("user_id"),)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ProfileSkill(Owned, Base):
    __tablename__ = "profile_skills"
    __table_args__ = (UniqueConstraint("user_id", "normalized"),)
    name: Mapped[str] = mapped_column(String(120))
    normalized: Mapped[str] = mapped_column(String(120), index=True)
    category: Mapped[str] = mapped_column(String(120), default="technical")
    level: Mapped[int] = mapped_column(Integer, default=1)
    months: Mapped[int | None] = mapped_column(Integer)
    last_used: Mapped[str | None] = mapped_column(String(10))
    developing: Mapped[bool] = mapped_column(Boolean, default=False)


class Evidence(Owned, Base):
    __tablename__ = "evidence"
    skill_id: Mapped[str] = mapped_column(
        ForeignKey("profile_skills.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=1)


class Document(Owned, Base):
    __tablename__ = "documents"
    name: Mapped[str] = mapped_column(String(240))
    kind: Mapped[str] = mapped_column(String(40), default="resume")
    content_type: Mapped[str] = mapped_column(String(120), default="text/plain")
    content: Mapped[bytes | None] = mapped_column(LargeBinary)
    text: Mapped[str] = mapped_column(Text, default="")
    extracted: Mapped[dict | None] = mapped_column(JSON)
    parent_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))


class JobSource(Owned, Base):
    __tablename__ = "job_sources"
    provider: Mapped[str] = mapped_column(String(40))
    board: Mapped[str] = mapped_column(String(120))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    __table_args__ = (UniqueConstraint("user_id", "provider", "board"),)


class Job(Owned, Base):
    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("user_id", "fingerprint"),)
    title: Mapped[str] = mapped_column(String(240), index=True)
    company: Mapped[str] = mapped_column(String(240), index=True)
    location: Mapped[str] = mapped_column(String(240), default="")
    description: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100), default="manual")
    external_id: Mapped[str | None] = mapped_column(String(160))
    fingerprint: Mapped[str] = mapped_column(String(64))
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    work_model: Mapped[str] = mapped_column(String(40), default="unknown", index=True)
    seniority: Mapped[str] = mapped_column(String(40), default="unknown", index=True)
    salary_min: Mapped[float | None] = mapped_column(Float)
    salary_max: Mapped[float | None] = mapped_column(Float)
    favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float | None] = mapped_column(Float, index=True)
    classification: Mapped[str | None] = mapped_column(String(40), index=True)
    coverage: Mapped[float | None] = mapped_column(Float)


class JobRequirement(Owned, Base):
    __tablename__ = "job_requirements"
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    skill: Mapped[str] = mapped_column(String(120), index=True)
    mandatory: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str] = mapped_column(Text, default="")


class MatchAnalysis(Owned, Base):
    __tablename__ = "match_analyses"
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float)
    classification: Mapped[str] = mapped_column(String(40))
    algorithm: Mapped[str] = mapped_column(String(30))
    input_hash: Mapped[str] = mapped_column(String(64))
    snapshot: Mapped[dict] = mapped_column(JSON)
    result: Mapped[dict] = mapped_column(JSON)


class MatchComponent(Owned, Base):
    __tablename__ = "match_components"
    analysis_id: Mapped[str] = mapped_column(
        ForeignKey("match_analyses.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(80))
    score: Mapped[float | None] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)


class Application(Owned, Base):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "job_id"),)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(50), default="discovered", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    resume_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    rejection_reason: Mapped[str | None] = mapped_column(Text)


class ApplicationEvent(Owned, Base):
    __tablename__ = "application_events"
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(300))
    data: Mapped[dict] = mapped_column(JSON, default=dict)


class Note(Owned, Base):
    __tablename__ = "notes"
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    body: Mapped[str] = mapped_column(Text)


class Contact(Owned, Base):
    __tablename__ = "contacts"
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(240))
    email: Mapped[str | None] = mapped_column(String(320))
    url: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(240), default="")


class MessageDraft(Owned, Base):
    __tablename__ = "message_drafts"
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(60))
    body: Mapped[str] = mapped_column(Text)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime)


class FollowUp(Owned, Base):
    __tablename__ = "follow_ups"
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    due_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)


class Interview(Owned, Base):
    __tablename__ = "interviews"
    application_id: Mapped[str] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(240))
    scheduled_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    kind: Mapped[str] = mapped_column(String(40))
    notes: Mapped[str] = mapped_column(Text, default="")
    feedback: Mapped[str] = mapped_column(Text, default="")
    preparation: Mapped[dict | None] = mapped_column(JSON)
    checklist: Mapped[list] = mapped_column(JSON, default=list)


class AIConversation(Owned, Base):
    __tablename__ = "ai_conversations"
    job_id: Mapped[str | None] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(240), default="Career Coach")


class AIMessage(Owned, Base):
    __tablename__ = "ai_messages"
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("ai_conversations.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20))
    body: Mapped[str] = mapped_column(Text)


class AIUsage(Owned, Base):
    __tablename__ = "ai_usage"
    kind: Mapped[str] = mapped_column(String(60))
    model: Mapped[str] = mapped_column(String(80))
    prompt_version: Mapped[str] = mapped_column(String(30))
    cache_key: Mapped[str] = mapped_column(String(64), index=True)
    output: Mapped[dict | None] = mapped_column(JSON)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="running")


class Task(Owned, Base):
    __tablename__ = "tasks"
    kind: Mapped[str] = mapped_column(String(60))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime)
    result: Mapped[dict | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)


class Notification(Owned, Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "key"),)
    key: Mapped[str] = mapped_column(String(160))
    title: Mapped[str] = mapped_column(String(300))
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    read: Mapped[bool] = mapped_column(Boolean, default=False)
