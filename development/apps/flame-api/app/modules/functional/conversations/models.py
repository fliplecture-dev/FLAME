"""Owned sessions, messages, and idempotent answer requests (B2.4)."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ConversationSession(Base):
    __tablename__ = "sessions"
    __table_args__ = (
        UniqueConstraint("id", "student_id"),
        CheckConstraint("mode IN ('study', 'curiosity')", name="mode_valid"),
        CheckConstraint("revision IS NULL OR revision >= 1", name="revision_positive"),
        CheckConstraint("(mode = 'study' AND curriculum_id IS NOT NULL AND revision IS NOT NULL AND context_snapshot IS NOT NULL) OR (mode = 'curiosity' AND curriculum_id IS NULL)", name="mode_context_valid"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.student_profiles.id", ondelete="RESTRICT"), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    curriculum_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.curricula.id", ondelete="RESTRICT"))
    revision: Mapped[int | None] = mapped_column(Integer)
    context_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    recent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("session_id", "turn_number", "role"),
        CheckConstraint("turn_number >= 1", name="turn_positive"),
        CheckConstraint("role IN ('user', 'assistant')", name="role_valid"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.sessions.id", ondelete="RESTRICT"), nullable=False)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    blocks: Mapped[list] = mapped_column(JSONB, nullable=False)
    resolved_curriculum_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.curricula.id", ondelete="RESTRICT"))
    resolved_subject_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.subjects.id", ondelete="RESTRICT"))
    resolved_topic_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.topics.id", ondelete="RESTRICT"))
    resolved_revision: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AnswerRequest(Base):
    __tablename__ = "answer_requests"
    __table_args__ = (
        UniqueConstraint("student_id", "session_id", "idempotency_key"),
        ForeignKeyConstraint(["session_id", "student_id"], ["flame.sessions.id", "flame.sessions.student_id"], ondelete="RESTRICT"),
        CheckConstraint("status IN ('pending', 'completed', 'failed')", name="status_valid"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.student_profiles.id", ondelete="RESTRICT"), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'pending'"))
    result: Mapped[dict | None] = mapped_column(JSONB)
    prompt_version: Mapped[str | None] = mapped_column(String(64))
    profile_version: Mapped[str | None] = mapped_column(String(64))
    model: Mapped[str | None] = mapped_column(String(128))
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    claim_token: Mapped[str | None] = mapped_column(String(64))
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())




class PendingClarification(Base):
    """One unresolved Curiosity question bound to an owned session."""
    __tablename__ = "pending_clarifications"
    __table_args__ = (
        ForeignKeyConstraint(["session_id", "student_id"], ["flame.sessions.id", "flame.sessions.student_id"], ondelete="RESTRICT"),
        CheckConstraint("status IN ('pending', 'resolved', 'cancelled', 'expired')", name="status_valid"),
        Index("ix_pending_clarifications_session_status", "session_id", "status"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.student_profiles.id", ondelete="RESTRICT"), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    question: Mapped[str] = mapped_column(String(4000), nullable=False)
    candidates: Mapped[list] = mapped_column(JSONB, nullable=False)
    selected_path: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'pending'"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())



