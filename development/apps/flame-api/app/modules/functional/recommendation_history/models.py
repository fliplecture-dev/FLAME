"""Recommendation-owned mapping of the existing table. No schema or data migration."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class RecommendationSet(Base):
    __tablename__ = "recommendation_sets"
    __table_args__ = (UniqueConstraint("message_id", name="uq_recommendation_sets_message"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.student_profiles.id", ondelete="RESTRICT"), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.sessions.id", ondelete="RESTRICT"), nullable=False)
    message_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.messages.id", ondelete="RESTRICT"), nullable=False)
    resource_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    teacher_ids: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    image_decision: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
