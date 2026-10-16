"""Persisted curriculum workbook upload, preview, commit, and provenance records."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CurriculumImport(Base):
    __tablename__ = "curriculum_imports"
    __table_args__ = (
        CheckConstraint("status IN ('uploaded', 'previewed', 'committed')", name="status_valid"),
        CheckConstraint("issue_count >= 0", name="issue_count_nonnegative"),
        Index("ix_curriculum_imports_curriculum_created", "curriculum_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    curriculum_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.curricula.id", ondelete="RESTRICT"), nullable=False)
    owner_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    file_bytes: Mapped[bytes | None] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="uploaded")
    sheet_levels: Mapped[dict | None] = mapped_column(JSONB)
    preview_revision: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    base_revision: Mapped[int | None] = mapped_column(Integer)
    preview_rows: Mapped[list | None] = mapped_column(JSONB)
    preview_result: Mapped[dict | None] = mapped_column(JSONB)
    issue_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    committed_result: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    committed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    payload_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CurriculumImportCommit(Base):
    __tablename__ = "curriculum_import_commits"
    __table_args__ = (UniqueConstraint("owner_subject", "idempotency_key", name="uq_import_commit_owner_key"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    import_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.curriculum_imports.id", ondelete="RESTRICT"), nullable=False)
    owner_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CurriculumImportSource(Base):
    __tablename__ = "curriculum_import_sources"
    __table_args__ = (UniqueConstraint("topic_id", "subtopic_id", "source_text", name="uq_import_source_path_text"),)

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    curriculum_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.curricula.id", ondelete="RESTRICT"), nullable=False)
    topic_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.topics.id", ondelete="RESTRICT"), nullable=False)
    subtopic_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.subtopics.id", ondelete="RESTRICT"))
    source_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    first_import_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.curriculum_imports.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
