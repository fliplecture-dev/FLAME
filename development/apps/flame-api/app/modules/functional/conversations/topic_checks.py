"""Owned, idempotent school-topic gate events."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TopicCheckEvent(Base):
    __tablename__ = "topic_check_events"
    __table_args__ = (
        UniqueConstraint("student_id", "session_id", "idempotency_key"),
        UniqueConstraint("clarification_id"),
        ForeignKeyConstraint(["session_id", "student_id"],
                             ["flame.sessions.id", "flame.sessions.student_id"], ondelete="RESTRICT"),
        CheckConstraint("status IN ('ready', 'clarification', 'out_of_scope', 'cancelled')",
                        name="status_valid"),
        Index("ix_topic_check_events_session_created", "session_id", "created_at", "id"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True),
        ForeignKey("flame.student_profiles.id", ondelete="RESTRICT"), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str] = mapped_column(String(4000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    clarification_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True),
        ForeignKey("flame.pending_clarifications.id", ondelete="RESTRICT"))
    choice_hash: Mapped[str | None] = mapped_column(String(64))
    context_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    response: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True),
        nullable=False, server_default=func.now())
