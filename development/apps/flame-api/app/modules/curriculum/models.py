"""Curriculum-owned hierarchy and revision tables (B2.3)."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Curriculum(Base):
    __tablename__ = "curricula"
    __table_args__ = (
        CheckConstraint("state IN ('draft', 'published', 'archived')", name="state_valid"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("revision >= 0", name="revision_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000))
    state: Mapped[str] = mapped_column(String(16), nullable=False, server_default=text("'draft'"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Level(Base):
    __tablename__ = "levels"
    __table_args__ = (
        UniqueConstraint("curriculum_id", "normalized_code", name="uq_levels_curriculum_code"),
        UniqueConstraint("id", "curriculum_id", name="uq_levels_id_curriculum"),
        UniqueConstraint("curriculum_id", "normalized_name", name="uq_levels_curriculum_name"),
        CheckConstraint("version >= 1", name="version_positive"),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    curriculum_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.curricula.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_code: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class Subject(Base):
    __tablename__ = "subjects"
    __table_args__ = (UniqueConstraint("level_id", "normalized_name"), UniqueConstraint("id", "level_id", name="uq_subjects_id_level"), CheckConstraint("display_order >= 0", name="display_order_nonnegative"))

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    level_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.levels.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class Domain(Base):
    __tablename__ = "domains"
    __table_args__ = (UniqueConstraint("subject_id", "normalized_name"), CheckConstraint("display_order >= 0", name="display_order_nonnegative"))

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.subjects.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("domain_id", "normalized_name"),
        UniqueConstraint("id", "domain_id"),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.domains.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class Topic(Base):
    __tablename__ = "topics"
    __table_args__ = (
        ForeignKeyConstraint(["category_id", "domain_id"], ["flame.categories.id", "flame.categories.domain_id"], ondelete="RESTRICT"),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    domain_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.domains.id", ondelete="RESTRICT"), nullable=False)
    category_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    learning_outcome: Mapped[str | None] = mapped_column(String(2000))
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


Index("uq_topics_categorized_path", Topic.domain_id, Topic.category_id, Topic.normalized_name, unique=True, postgresql_where=Topic.category_id.is_not(None))
Index("uq_topics_uncategorized_path", Topic.domain_id, Topic.normalized_name, unique=True, postgresql_where=Topic.category_id.is_(None))


class Subtopic(Base):
    __tablename__ = "subtopics"
    __table_args__ = (UniqueConstraint("topic_id", "normalized_name"), UniqueConstraint("id", "topic_id", name="uq_subtopics_id_topic"), CheckConstraint("display_order >= 0", name="display_order_nonnegative"))

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    topic_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.topics.id", ondelete="RESTRICT"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))


class CurriculumRevision(Base):
    __tablename__ = "curriculum_revisions"
    __table_args__ = (UniqueConstraint("curriculum_id", "number"), CheckConstraint("number >= 1", name="number_positive"))

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    curriculum_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.curricula.id", ondelete="RESTRICT"), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

class CurriculumDraft(Base):
    """Private editable hierarchy snapshot; published catalogue rows stay untouched."""

    __tablename__ = "curriculum_drafts"
    __table_args__ = (
        CheckConstraint("base_revision >= 0", name="base_revision_nonnegative"),
        CheckConstraint("revision >= 1", name="revision_positive"),
    )

    curriculum_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("flame.curricula.id", ondelete="RESTRICT"), primary_key=True)
    base_revision: Mapped[int] = mapped_column(Integer, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    paths: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    source_import_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    updated_by_subject: Mapped[str | None] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
