"""Multi-topic activity kit catalogue (B2.5)."""
from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ActivityKit(Base):
    __tablename__ = "activity_kits"
    learning_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    __table_args__ = (
        CheckConstraint("jsonb_typeof(learning_metadata) = 'object'", name="learning_metadata_object"),
        CheckConstraint("cost IS NULL OR cost >= 0", name="cost_nonnegative"),
        CheckConstraint("(cost IS NULL) = (currency IS NULL)", name="cost_currency_together"),
        CheckConstraint("currency IS NULL OR currency ~ '^[A-Z]{3}$'", name="currency_format"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000))
    image_keys: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    materials: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    instructions: Mapped[str | None] = mapped_column(String(10000))
    supervision: Mapped[str | None] = mapped_column(String(4000))
    cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    currency: Mapped[str | None] = mapped_column(String(3))
    availability: Mapped[str | None] = mapped_column(String(255))
    supplier_url: Mapped[str | None] = mapped_column(String(2048))
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class KitTopic(Base):
    __tablename__ = "kit_topics"
    __table_args__ = (
        ForeignKeyConstraint(["subtopic_id", "topic_id"], ["flame.subtopics.id", "flame.subtopics.topic_id"], ondelete="RESTRICT"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    kit_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.activity_kits.id", ondelete="RESTRICT"), nullable=False)
    topic_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.topics.id", ondelete="RESTRICT"), nullable=False)
    subtopic_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))


Index("uq_kit_topic_only", KitTopic.kit_id, KitTopic.topic_id, unique=True, postgresql_where=KitTopic.subtopic_id.is_(None))
Index("uq_kit_subtopic", KitTopic.kit_id, KitTopic.topic_id, KitTopic.subtopic_id, unique=True, postgresql_where=KitTopic.subtopic_id.is_not(None))
