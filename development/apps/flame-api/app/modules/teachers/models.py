"""Teacher catalogue and reviewed expertise mappings (B2.5)."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Teacher(Base):
    __tablename__ = "teachers"
    learning_metadata: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    __table_args__ = (CheckConstraint("jsonb_typeof(learning_metadata) = 'object'", name="learning_metadata_object"),)
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str | None] = mapped_column(String(4000))
    qualifications: Mapped[str | None] = mapped_column(String(4000))
    experience: Mapped[str | None] = mapped_column(String(4000))
    languages: Mapped[list] = mapped_column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    availability: Mapped[str | None] = mapped_column(String(255))
    published: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class TeacherExpertise(Base):
    __tablename__ = "teacher_expertise"
    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    teacher_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.teachers.id", ondelete="RESTRICT"), nullable=False)
    subject_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.subjects.id", ondelete="RESTRICT"), nullable=False)
    topic_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("flame.topics.id", ondelete="RESTRICT"))
    claim_status: Mapped[str] = mapped_column(String(24), nullable=False, server_default=text("'declared'"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


Index("uq_teacher_subject_expertise", TeacherExpertise.teacher_id, TeacherExpertise.subject_id, unique=True, postgresql_where=TeacherExpertise.topic_id.is_(None))
Index("uq_teacher_topic_expertise", TeacherExpertise.teacher_id, TeacherExpertise.subject_id, TeacherExpertise.topic_id, unique=True, postgresql_where=TeacherExpertise.topic_id.is_not(None))
