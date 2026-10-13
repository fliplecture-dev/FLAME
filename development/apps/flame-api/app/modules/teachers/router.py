"""Admin teacher catalogue and reviewed/declared expertise mappings."""
from app.contracts.learning_metadata import LearningMetadata, metadata_data
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, func, or_, select

from app.modules.curriculum.models import Curriculum, Domain, Level, Subject, Topic
from app.modules.identity.dependencies import require_admin
from app.modules.resources.service import fail, path_info
from app.modules.teachers.models import Teacher, TeacherExpertise

router = APIRouter(prefix="/api/v1/admin/teachers", tags=["admin-teachers"])
Admin = Annotated[dict, Depends(require_admin)]


class ExpertiseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject_id: UUID
    topic_id: UUID | None = None
    claim_status: str = "declared"

    @field_validator("claim_status")
    @classmethod
    def valid_claim(cls, value):
        if value not in ("declared", "reviewed"):
            raise ValueError("invalid_claim_status")
        return value


class TeacherDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learning_metadata: LearningMetadata = Field(default_factory=LearningMetadata)
    name: str = Field(min_length=1, max_length=255)
    bio: str | None = Field(default=None, max_length=4000)
    qualifications: str | None = Field(default=None, max_length=4000)
    experience: str | None = Field(default=None, max_length=4000)
    languages: list[str] = Field(default_factory=list, max_length=20)
    availability: str | None = Field(default=None, max_length=255)
    expertise: list[ExpertiseInput] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate(self):
        if not self.name.strip() or any(not value.strip() or len(value) > 80 for value in self.languages):
            raise ValueError("invalid_teacher_metadata")
        if len({(e.subject_id, e.topic_id) for e in self.expertise}) != len(self.expertise):
            raise ValueError("duplicate_expertise")
        return self


class TeacherEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learning_metadata: LearningMetadata | None = None
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = Field(default=None, max_length=4000)
    qualifications: str | None = Field(default=None, max_length=4000)
    experience: str | None = Field(default=None, max_length=4000)
    languages: list[str] | None = Field(default=None, max_length=20)
    availability: str | None = Field(default=None, max_length=255)
    expertise: list[ExpertiseInput] | None = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate(self):
        if self.name is not None and not self.name.strip():
            raise ValueError("teacher_name_required")
        if self.languages is not None and any(not value.strip() or len(value) > 80 for value in self.languages):
            raise ValueError("invalid_languages")
        if self.expertise is not None and len({(e.subject_id, e.topic_id) for e in self.expertise}) != len(self.expertise):
            raise ValueError("duplicate_expertise")
        return self


class VersionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


def db(request):
    return request.app.state.database


def expertise_valid(session, item: ExpertiseInput, published: bool = False):
    subject = session.get(Subject, item.subject_id)
    if subject is None or subject.archived:
        fail(422, "invalid_teacher_subject")
    level = session.get(Level, subject.level_id)
    curriculum = session.get(Curriculum, level.curriculum_id) if level else None
    if level is None or level.archived or curriculum is None or curriculum.state == "archived":
        fail(422, "invalid_teacher_subject")
    if published and curriculum.state != "published":
        fail(422, "published_subject_required")
    if item.topic_id:
        path = path_info(session, item.topic_id, published=published)
        if path["subject_id"] != item.subject_id:
            fail(422, "teacher_topic_subject_mismatch")


def teacher_data(session, row):
    expertise = session.scalars(select(TeacherExpertise).where(TeacherExpertise.teacher_id == row.id)
                                .order_by(TeacherExpertise.subject_id, TeacherExpertise.topic_id)).all()
    return {"learning_metadata": metadata_data(row.learning_metadata), "id": str(row.id), "name": row.name, "bio": row.bio, "qualifications": row.qualifications,
            "experience": row.experience, "languages": row.languages, "availability": row.availability,
            "published": row.published, "version": row.version,
            "expertise": [{"subject_id": str(e.subject_id),
                           "topic_id": str(e.topic_id) if e.topic_id else None,
                           "claim_status": e.claim_status,
                           "reviewed_at": e.reviewed_at.isoformat() if e.reviewed_at else None} for e in expertise]}


def replace_expertise(session, row, items):
    for item in items:
        expertise_valid(session, item)
    session.execute(delete(TeacherExpertise).where(TeacherExpertise.teacher_id == row.id))
    session.flush()
    for item in items:
        session.add(TeacherExpertise(teacher_id=row.id, subject_id=item.subject_id,
                   topic_id=item.topic_id, claim_status=item.claim_status,
                   reviewed_at=datetime.now(timezone.utc) if item.claim_status == "reviewed" else None))


def publication_check(session, row):
    if not row.name.strip():
        fail(422, "teacher_name_required")
    expertise = session.scalars(select(TeacherExpertise).where(TeacherExpertise.teacher_id == row.id)).all()
    if not expertise:
        fail(422, "teacher_expertise_required")
    for item in expertise:
        expertise_valid(session, ExpertiseInput(subject_id=item.subject_id, topic_id=item.topic_id,
                                                claim_status=item.claim_status), published=True)


@router.get("")
def list_teachers(request: Request, _: Admin, q: str = Query("", max_length=255),
                  published: bool | None = None, subject_id: UUID | None = None,
                  offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    with db(request).session() as session:
        query = select(Teacher)
        if q.strip():
            query = query.where(or_(Teacher.name.ilike("%" + q.strip() + "%"),
                                    Teacher.bio.ilike("%" + q.strip() + "%")))
        if published is not None:
            query = query.where(Teacher.published == published)
        if subject_id:
            query = query.where(Teacher.id.in_(select(TeacherExpertise.teacher_id)
                                                .where(TeacherExpertise.subject_id == subject_id)))
        total = session.scalar(select(func.count()).select_from(query.subquery()))
        rows = session.scalars(query.order_by(Teacher.name, Teacher.id).offset(offset).limit(limit)).all()
        return {"items": [teacher_data(session, row) for row in rows], "total": total,
                "offset": offset, "limit": limit}


@router.post("", status_code=201)
def create_teacher(request: Request, _: Admin, body: TeacherDraft):
    with db(request).session() as session, session.begin():
        row = Teacher(name=body.name.strip(), learning_metadata=metadata_data(body.learning_metadata), bio=body.bio, qualifications=body.qualifications,
                      experience=body.experience, languages=body.languages, availability=body.availability)
        session.add(row)
        session.flush()
        replace_expertise(session, row, body.expertise)
        session.flush()
        result = teacher_data(session, row)
    return result


@router.get("/{teacher_id}")
def teacher_detail(request: Request, _: Admin, teacher_id: UUID):
    with db(request).session() as session:
        row = session.get(Teacher, teacher_id)
        if row is None:
            fail(404, "teacher_not_found")
        return teacher_data(session, row)


@router.patch("/{teacher_id}")
def edit_teacher(request: Request, _: Admin, teacher_id: UUID, body: TeacherEdit):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(Teacher).where(Teacher.id == teacher_id).with_for_update())
        if row is None:
            fail(404, "teacher_not_found")
        if row.version != body.expected_version:
            fail(409, "stale_version")
        if "learning_metadata" in body.model_fields_set:
            if body.learning_metadata is None:
                fail(422, "learning_metadata_required")
            row.learning_metadata = metadata_data(body.learning_metadata)
        for field in ("name", "bio", "qualifications", "experience", "languages", "availability"):
            if field in body.model_fields_set:
                setattr(row, field, getattr(body, field))
        if body.expertise is not None:
            replace_expertise(session, row, body.expertise)
        row.version += 1
        session.flush()
        if row.published:
            publication_check(session, row)
        result = teacher_data(session, row)
    return result


@router.post("/{teacher_id}/publish")
def publish_teacher(request: Request, _: Admin, teacher_id: UUID, body: VersionBody):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(Teacher).where(Teacher.id == teacher_id).with_for_update())
        if row is None:
            fail(404, "teacher_not_found")
        if row.version != body.expected_version:
            fail(409, "stale_version")
        publication_check(session, row)
        row.published = True
        row.version += 1
        session.flush()
        result = teacher_data(session, row)
    return result


@router.post("/{teacher_id}/unpublish")
def unpublish_teacher(request: Request, _: Admin, teacher_id: UUID, body: VersionBody):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(Teacher).where(Teacher.id == teacher_id).with_for_update())
        if row is None:
            fail(404, "teacher_not_found")
        if row.version != body.expected_version:
            fail(409, "stale_version")
        row.published = False
        row.version += 1
        session.flush()
        result = teacher_data(session, row)
    return result
