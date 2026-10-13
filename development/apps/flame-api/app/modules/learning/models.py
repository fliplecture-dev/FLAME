"""Student-owned My Learning paths (B2.4)."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, func, text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class LearningMembership(Base):
    __tablename__ = "learning_memberships"
    __table_args__ = (
        ForeignKeyConstraint(["level_id", "curriculum_id"], ["flame.levels.id", "flame.levels.curriculum_id"], ondelete="RESTRICT"),
        ForeignKeyConstraint(["subject_id", "level_id"], ["flame.subjects.id", "flame.subjects.level_id"], ondelete="RESTRICT"),
        CheckConstraint("subject_id IS NULL OR level_id IS NOT NULL", name="subject_requires_level"),
        CheckConstraint("(domain_id IS NULL OR subject_id IS NOT NULL) AND (topic_id IS NULL OR domain_id IS NOT NULL) AND (subtopic_id IS NULL OR topic_id IS NOT NULL)", name="learning_path_depth"),
        CheckConstraint("version >= 1", name="version_positive"),
    )
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    student_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.student_profiles.id", ondelete="RESTRICT"), nullable=False)
    curriculum_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.curricula.id", ondelete="RESTRICT"), nullable=False)
    level_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    subject_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True))
    domain_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.domains.id", ondelete="RESTRICT"))
    category_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.categories.id", ondelete="RESTRICT"))
    topic_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.topics.id", ondelete="RESTRICT"))
    subtopic_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.subtopics.id", ondelete="RESTRICT"))
    visible: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


Index("uq_learning_curriculum_path", LearningMembership.student_id, LearningMembership.curriculum_id, unique=True, postgresql_where=LearningMembership.level_id.is_(None))
Index("uq_learning_level_path", LearningMembership.student_id, LearningMembership.curriculum_id, LearningMembership.level_id, unique=True, postgresql_where=(LearningMembership.level_id.is_not(None) & LearningMembership.subject_id.is_(None)))
Index("uq_learning_subject_path", LearningMembership.student_id, LearningMembership.curriculum_id, LearningMembership.level_id, LearningMembership.subject_id, unique=True, postgresql_where=(LearningMembership.subject_id.is_not(None) & LearningMembership.domain_id.is_(None)))

Index("uq_learning_domain_path", LearningMembership.student_id, LearningMembership.domain_id, unique=True, postgresql_where=(LearningMembership.domain_id.is_not(None) & LearningMembership.topic_id.is_(None)))
Index("uq_learning_topic_path", LearningMembership.student_id, LearningMembership.topic_id, unique=True, postgresql_where=(LearningMembership.topic_id.is_not(None) & LearningMembership.subtopic_id.is_(None)))
Index("uq_learning_subtopic_path", LearningMembership.student_id, LearningMembership.subtopic_id, unique=True, postgresql_where=LearningMembership.subtopic_id.is_not(None))
