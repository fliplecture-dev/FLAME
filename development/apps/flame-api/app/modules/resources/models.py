"""B9.2 approved media metadata and curriculum associations."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, validates
from app.core.database import Base


class Resource(Base):
    @validates("type")
    def normalize_type(self, key, value):
        from app.modules.resources.validation import canonical_type
        return canonical_type(value)

    __tablename__ = "resources"
    learning_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    __table_args__ = (
        CheckConstraint("jsonb_typeof(learning_metadata) = 'object'", name="learning_metadata_object"),
        CheckConstraint("(storage_key IS NULL) <> (external_url IS NULL) OR (type = 'interactive' AND NOT published AND storage_key IS NULL AND external_url IS NULL)", name="one_media_source"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("type IN ('image', 'video', 'interactive') OR (type = 'audio' AND legacy_media IS NOT NULL AND NOT published AND availability = 'unavailable')", name="media_family"),
        CheckConstraint("byte_size IS NULL OR byte_size > 0", name="byte_size_positive"),
        CheckConstraint("availability IN ('available', 'unavailable')", name="availability_valid"),
        CheckConstraint("rights_basis IS NULL OR rights_basis IN ('owned', 'licensed', 'permission')", name="rights_basis_valid"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    external_url: Mapped[str | None] = mapped_column(String(2048))
    thumbnail_storage_key: Mapped[str | None] = mapped_column(String(1024))
    external_video: Mapped[dict | None] = mapped_column(JSONB)
    legacy_media: Mapped[dict | None] = mapped_column(JSONB)
    mime_type: Mapped[str | None] = mapped_column(String(100))
    byte_size: Mapped[int | None] = mapped_column(Integer)
    rights_basis: Mapped[str | None] = mapped_column(String(24))
    rights_holder: Mapped[str | None] = mapped_column(String(255))
    rights_reference: Mapped[str | None] = mapped_column(String(2048))
    attribution: Mapped[str | None] = mapped_column(String(2000))
    distribution_scope: Mapped[str | None] = mapped_column(String(255))
    alt_text: Mapped[str | None] = mapped_column(String(1000))
    caption_or_transcript: Mapped[str | None] = mapped_column(String(10000))
    accessibility_note: Mapped[str | None] = mapped_column(String(1000))
    availability: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'available'"))
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_by: Mapped[str | None] = mapped_column(String(255))
    deletion_snapshot: Mapped[dict | None] = mapped_column(JSONB)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ResourceUpload(Base):
    @validates("media_type")
    def normalize_media_type(self, key, value):
        return "video" if value == "animation" else value

    __tablename__ = "resource_uploads"
    __table_args__ = (
        CheckConstraint("byte_size > 0", name="byte_size_positive"),
        CheckConstraint("NOT (resource_id IS NOT NULL AND kit_id IS NOT NULL)", name="one_upload_owner"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False, unique=True)
    owner_auth_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    file_name: Mapped[str | None] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    media_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.resources.id", ondelete="RESTRICT"))
    kit_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.activity_kits.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class ResourceTopic(Base):
    __tablename__ = "resource_topics"
    __table_args__ = (
        ForeignKeyConstraint(["subtopic_id", "topic_id"], ["flame.subtopics.id", "flame.subtopics.topic_id"], ondelete="RESTRICT"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    resource_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.resources.id", ondelete="RESTRICT"), nullable=False)
    topic_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.topics.id", ondelete="RESTRICT"), nullable=False)
    subtopic_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))


Index("uq_resource_topic_only", ResourceTopic.resource_id, ResourceTopic.topic_id, unique=True, postgresql_where=ResourceTopic.subtopic_id.is_(None))
Index("uq_resource_subtopic", ResourceTopic.resource_id, ResourceTopic.topic_id, ResourceTopic.subtopic_id, unique=True, postgresql_where=ResourceTopic.subtopic_id.is_not(None))


# Compatibility alias; the table is registered exactly once by its owner.
from app.modules.recommendations.models import RecommendationSet  # noqa: F401,E402
