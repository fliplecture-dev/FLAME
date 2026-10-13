"""Protected B4 catalogue, import, My Learning and student directory routes."""
from typing import Annotated, Literal
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from app.modules.curriculum.deletion import deletion_review, delete_curriculum_records
from app.modules.curriculum.drafts import (
    draft_tree, publish_draft, rebase_state_only_draft, rename_draft_node, save_draft_changes,
)
from app.modules.curriculum.path_batch import apply_path_batch
from app.modules.curriculum.catalogue import (
    ancestor_curriculum, curriculum_or_404, fail, nodes, subject_path, tree, validate_publishable,
)
from app.modules.curriculum.import_service import CurriculumImportService, ImportFailure
from app.modules.curriculum.import_models import CurriculumImport
from app.modules.curriculum.models import Category, Curriculum, CurriculumDraft, CurriculumRevision, Domain, Level, Subject, Subtopic, Topic
from app.modules.curriculum.workbook_parser import WorkbookRejected, match_key, MAX_FILE_BYTES
from app.modules.curriculum.workbook_export import export_workbook
from app.modules.identity.dependencies import require_admin, require_member
from app.modules.identity.models import AdminRole, StudentProfile
from app.modules.learning.models import LearningMembership

router = APIRouter(prefix="/api/v1")
Member = Annotated[dict, Depends(require_member)]
Admin = Annotated[dict, Depends(require_admin)]


class CurriculumCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("code", "name")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Required")
        return value.strip()


class ChildCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parent_id: UUID
    category_id: UUID | None = None
    name: str = Field(min_length=1, max_length=255)
    display_order: int | None = Field(default=None, ge=0)
    learning_outcome: str | None = Field(default=None, max_length=2000)
    subtopic_name: str | None = Field(default=None, min_length=1, max_length=255)

    @field_validator("name", "subtopic_name")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Required")
        return value.strip() if value is not None else None


class EditBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    learning_outcome: str | None = Field(default=None, max_length=2000)

    @field_validator("name")
    @classmethod
    def nonblank(cls, value):
        if value is not None and not value.strip():
            raise ValueError("Required")
        return value.strip() if value is not None else None


class VersionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)

class PermanentDeleteBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    expected_revision: int = Field(ge=0)
    confirm: str = Field(min_length=1, max_length=255)


class PathValues(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: str = Field(min_length=1, max_length=80)
    subject: str = Field(min_length=1, max_length=255)
    domain: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=255)
    topic: str = Field(min_length=1, max_length=255)
    subtopic: str = Field(min_length=1, max_length=255)

    @field_validator("level", "subject", "domain", "topic", "subtopic")
    @classmethod
    def required_path_text(cls, value):
        if not value.strip():
            raise ValueError("Required")
        return value.strip()

    @field_validator("category")
    @classmethod
    def optional_path_text(cls, value):
        return value.strip() or None if value is not None else None


class PathChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    key: str = Field(min_length=1, max_length=100)
    action: Literal["upsert", "delete"]
    source_subtopic_id: UUID | None = None
    values: PathValues | None = None


class DraftRenameBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    field: Literal["level", "subject", "domain", "category", "topic", "subtopic"]
    node_id: UUID
    name: str = Field(min_length=1, max_length=255)


class PublishDraftBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    expected_draft_revision: int = Field(ge=0)


class PathBatchBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=0)
    changes: list[PathChange] = Field(min_length=1, max_length=100)




class PreviewBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet_levels: dict[str, str]


class CommitBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_revision: UUID
    confirm: str = Field(min_length=9, max_length=100)


class ReviewRowChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    sheet: str = Field(min_length=1, max_length=255)
    row_number: int | None = Field(default=None, ge=2)
    insert_before: int | None = Field(default=None, ge=2)
    action: Literal["upsert", "delete", "add"]
    values: list[str] | None = None


class ReviewChangesBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preview_revision: UUID
    changes: list[ReviewRowChange] = Field(min_length=1, max_length=100)


class LearningAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")
    curriculum_id: UUID
    level_id: UUID | None = None
    subject_id: UUID | None = None
    domain_id: UUID | None = None
    category_id: UUID | None = None
    topic_id: UUID | None = None
    subtopic_id: UUID | None = None


class VisibilityBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    visible: bool
    expected_version: int = Field(ge=1)


def db(request):
    return request.app.state.database


def revision(session, curriculum, kind, details=None):
    curriculum.revision += 1
    session.add(CurriculumRevision(curriculum_id=curriculum.id, number=curriculum.revision, change_kind=kind, details=details))


def profile_subject(session, principal):
    profile = session.get(StudentProfile, UUID(principal["id"]))
    if profile is None:
        fail(401, "profile_not_found")
    return profile.auth_subject


def importer(request):
    return CurriculumImportService(db(request).sessions)


def import_error(exc):
    code = exc.code if isinstance(exc, ImportFailure) else str(exc)
    if code in ("admin_required",):
        fail(403, code)
    if code in ("import_not_found", "curriculum_not_found"):
        fail(404, code)
    if code in ("already_committed", "stale_preview", "idempotency_conflict", "invalid_preview"):
        raise HTTPException(409, {"code": code, "revision_mismatch": getattr(exc, "revision_mismatch", None)})
    fail(422, code)


def membership_data(row):
    return {"id": str(row.id), "curriculum_id": str(row.curriculum_id),
            "level_id": str(row.level_id) if row.level_id else None,
            "subject_id": str(row.subject_id) if row.subject_id else None,
            "domain_id": str(row.domain_id) if row.domain_id else None,
            "category_id": str(row.category_id) if row.category_id else None,
            "topic_id": str(row.topic_id) if row.topic_id else None,
            "subtopic_id": str(row.subtopic_id) if row.subtopic_id else None,
            "visible": row.visible, "version": row.version, "created_at": row.created_at.isoformat()}


@router.get("/curricula")
def published_curricula(request: Request, _: Member, q: str = Query("", max_length=255)):
    with db(request).session() as session:
        query = select(Curriculum).where(Curriculum.state == "published")
        if q.strip():
            query = query.where(or_(Curriculum.name.ilike("%" + q.strip() + "%"),
                                    Curriculum.code.ilike("%" + q.strip() + "%")))
        rows = session.scalars(query.order_by(Curriculum.name, Curriculum.id).limit(100)).all()
        return {"items": [{"id": str(c.id), "code": c.code, "name": c.name,
                           "description": c.description, "revision": c.revision} for c in rows]}


@router.get("/curricula/search")
def search_published_paths(request: Request, _: Member, q: str = Query(min_length=1, max_length=255),
                           offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100)):
    term = "%" + q.strip() + "%"
    if len(q.strip()) < 2:
        fail(422, "search_term_too_short")
    with db(request).session() as session:
        query = (select(Curriculum, Level, Subject, Domain, Category, Topic, Subtopic)
                 .join(Level, Level.curriculum_id == Curriculum.id)
                 .join(Subject, Subject.level_id == Level.id)
                 .join(Domain, Domain.subject_id == Subject.id)
                 .join(Topic, Topic.domain_id == Domain.id)
                 .outerjoin(Category, Category.id == Topic.category_id)
                 .join(Subtopic, Subtopic.topic_id == Topic.id)
                 .where(Curriculum.state == "published",
                        Level.archived.is_(False), Subject.archived.is_(False),
                        Domain.archived.is_(False), Topic.archived.is_(False),
                        Subtopic.archived.is_(False),
                        or_(Category.id.is_(None), Category.archived.is_(False)),
                        or_(Curriculum.name.ilike(term), Level.name.ilike(term),
                            Subject.name.ilike(term), Domain.name.ilike(term),
                            Topic.name.ilike(term), Subtopic.name.ilike(term)))
                 .order_by(Curriculum.name, Level.display_order, Subject.display_order,
                           Domain.display_order, Topic.display_order, Subtopic.display_order)
                 .offset(offset).limit(limit + 1))
        rows = session.execute(query).all()
        page = rows[:limit]
        return {"items": [
            {"curriculum_id": str(c.id), "level_id": str(l.id), "subject_id": str(s.id),
             "domain_id": str(d.id), "category_id": str(cat.id) if cat else None,
             "topic_id": str(t.id), "subtopic_id": str(st.id),
             "names": {"curriculum": c.name, "level": l.name, "subject": s.name,
                       "domain": d.name, "topic": t.name, "subtopic": st.name},
             "revision": c.revision}
            for c, l, s, d, cat, t, st in page],
            "next_offset": offset + limit if len(rows) > limit else None}


@router.get("/curricula/{curriculum_id}/tree")
def published_curriculum_tree(request: Request, curriculum_id: UUID, _: Member):
    with db(request).session() as session:
        return tree(session, curriculum_or_404(session, curriculum_id))


@router.get("/curricula/{curriculum_id}/levels")
def published_levels(request: Request, curriculum_id: UUID, _: Member):
    with db(request).session() as session:
        curriculum_or_404(session, curriculum_id)
        levels = session.scalars(select(Level).where(
            Level.curriculum_id == curriculum_id, Level.archived.is_(False)
        ).order_by(Level.display_order, Level.name)).all()
        return {"items": [{"id": str(n.id), "name": n.name, "display_order": n.display_order} for n in levels]}


@router.get("/curricula/{curriculum_id}/levels/{level_id}/tree")
def published_tree(request: Request, curriculum_id: UUID, level_id: UUID, _: Member):
    with db(request).session() as session:
        return tree(session, curriculum_or_404(session, curriculum_id), level_id=level_id)


@router.get("/admin/curricula")
def admin_curricula(request: Request, _: Admin, q: str = Query("", max_length=255),
                    offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)):
    with db(request).session() as session:
        query = select(Curriculum)
        if q.strip():
            query = query.where(or_(Curriculum.name.ilike("%" + q.strip() + "%"),
                                    Curriculum.code.ilike("%" + q.strip() + "%")))
        count = session.scalar(select(func.count()).select_from(query.subquery()))
        rows = session.scalars(query.order_by(Curriculum.created_at.desc(), Curriculum.id).offset(offset).limit(limit)).all()
        ids = [c.id for c in rows]
        drafts = {item.curriculum_id: item for item in session.scalars(select(CurriculumDraft).where(CurriculumDraft.curriculum_id.in_(ids))).all()} if ids else {}
        last_edits = dict(session.execute(select(CurriculumRevision.curriculum_id, func.max(CurriculumRevision.created_at))
            .where(CurriculumRevision.curriculum_id.in_(ids))
            .group_by(CurriculumRevision.curriculum_id)).all()) if rows else {}
        publications = dict(session.execute(select(CurriculumRevision.curriculum_id, func.max(CurriculumRevision.number))
            .where(CurriculumRevision.curriculum_id.in_(ids), CurriculumRevision.change_kind == "publish")
            .group_by(CurriculumRevision.curriculum_id)).all()) if rows else {}
        used_ids = set()
        if ids:
            used_ids.update(session.scalars(select(Level.curriculum_id).where(Level.curriculum_id.in_(ids))).all())
            used_ids.update(session.scalars(select(CurriculumImport.curriculum_id).where(CurriculumImport.curriculum_id.in_(ids))).all())
            used_ids.update(session.scalars(select(LearningMembership.curriculum_id).where(LearningMembership.curriculum_id.in_(ids))).all())
        return {"items": [{"id": str(c.id), "code": c.code, "name": c.name,
                           "state": c.state, "version": c.version, "revision": c.revision,
                           "published_revision": publications.get(c.id, 0),
                           "draft_revision": drafts[c.id].revision if c.id in drafts else 0,
                           "has_draft": c.id in drafts,
                           "updated_at": (last_edits.get(c.id) or c.created_at).isoformat(),
                           "can_delete": c.state == "draft" and c.revision == 0 and c.id not in used_ids} for c in rows],
                "total": count}


@router.post("/admin/curricula", status_code=201)
def create_curriculum(request: Request, body: CurriculumCreate, _: Admin):
    try:
        with db(request).session() as session, session.begin():
            row = Curriculum(code=body.code, normalized_code=match_key(body.code),
                             name=body.name, description=body.description)
            session.add(row)
            session.flush()
            result = {"id": str(row.id), "code": row.code, "name": row.name,
                      "state": row.state, "version": row.version, "revision": row.revision}
        return result
    except IntegrityError:
        fail(409, "duplicate_curriculum_code")


@router.delete("/admin/curricula/{curriculum_id}")
def delete_unused_draft(request: Request, curriculum_id: UUID, body: VersionBody, _: Admin):
    try:
        with db(request).session() as session, session.begin():
            row = curriculum_or_404(session, curriculum_id, published=False, lock=True)
            if row.version != body.expected_version:
                fail(409, "version_conflict")
            if row.state != "draft" or row.revision != 0:
                fail(409, "draft_in_use")
            if (session.scalar(select(Level.id).where(Level.curriculum_id == row.id).limit(1))
                    or session.scalar(select(CurriculumImport.id).where(CurriculumImport.curriculum_id == row.id).limit(1))
                    or session.scalar(select(LearningMembership.id).where(LearningMembership.curriculum_id == row.id).limit(1))):
                fail(409, "draft_in_use")
            session.delete(row)
        return {"id": str(curriculum_id), "status": "deleted"}
    except IntegrityError:
        fail(409, "draft_in_use")


@router.post("/admin/curricula/{curriculum_id}/paths/batch")
def save_path_rows(request: Request, curriculum_id: UUID, body: PathBatchBody,
                   principal: Admin):
    try:
        with db(request).session() as session, session.begin():
            curriculum = curriculum_or_404(session, curriculum_id, published=False, lock=True)
            owner = profile_subject(session, principal)
            return save_draft_changes(
                session, curriculum, body.expected_revision,
                [change.model_dump() for change in body.changes], owner)
    except IntegrityError:
        fail(409, "duplicate_or_referenced_path")


@router.post("/admin/curricula/{curriculum_id}/draft/rename")
def rename_draft(request: Request, curriculum_id: UUID, body: DraftRenameBody,
                 principal: Admin):
    with db(request).session() as session, session.begin():
        curriculum = curriculum_or_404(session, curriculum_id, published=False, lock=True)
        owner = profile_subject(session, principal)
        return rename_draft_node(
            session, curriculum, body.expected_revision, body.field,
            body.node_id, body.name, owner)

@router.get("/admin/curricula/{curriculum_id}/export")
def export_curriculum(request: Request, curriculum_id: UUID, _: Admin,
                      source: Literal["published", "draft", "revision"] = "draft",
                      revision_number: int | None = Query(default=None, ge=1)):
    with db(request).session() as session:
        curriculum = curriculum_or_404(session, curriculum_id, published=False)
        try:
            payload = export_workbook(session, curriculum, source, revision_number)
        except ValueError as exc:
            fail(422, str(exc))
        filename = f"{curriculum.code}-{source}.xlsx"
        return Response(
            content=payload,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"content-disposition": f'attachment; filename="{filename}"',
                     "cache-control": "no-store"})

@router.get("/admin/curricula/{curriculum_id}/deletion-review")
def review_permanent_deletion(request: Request, curriculum_id: UUID, _: Admin):
    with db(request).session() as session:
        row = session.get(Curriculum, curriculum_id)
        if row is None:
            fail(404, "curriculum_not_found")
        return deletion_review(session, row)


@router.post("/admin/curricula/{curriculum_id}/permanent")
def permanently_delete_curriculum(request: Request, curriculum_id: UUID,
                                  body: PermanentDeleteBody, principal: Admin):
    try:
        with db(request).session() as session, session.begin():
            row = session.scalar(select(Curriculum).where(
                Curriculum.id == curriculum_id).with_for_update())
            if row is None:
                fail(404, "curriculum_not_found")
            if body.expected_version != row.version or body.expected_revision != row.revision:
                fail(409, "version_conflict")
            if body.confirm.strip() not in (row.name, row.code):
                fail(422, "confirmation_mismatch")
            review = deletion_review(session, row)
            if not review["can_delete"]:
                raise HTTPException(409, {"code": "deletion_blocked", "review": review})
            deleted_id, deleted_code = str(row.id), row.code
            delete_curriculum_records(session, row)
        logging.getLogger(__name__).warning(
            "curriculum_permanently_deleted actor=%s curriculum=%s code=%s",
            principal.get("id"), deleted_id, deleted_code)
        return {"id": deleted_id, "status": "deleted", "removed": review["counts"]}
    except IntegrityError:
        fail(409, "dependencies_changed")


@router.post("/admin/curricula/{curriculum_id}/restore")
def restore_curriculum(request: Request, curriculum_id: UUID, body: VersionBody, _: Admin):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(Curriculum).where(
            Curriculum.id == curriculum_id).with_for_update())
        if row is None:
            fail(404, "curriculum_not_found")
        if row.version != body.expected_version:
            fail(409, "version_conflict")
        if row.state != "archived":
            fail(409, "not_archived")
        row.state = "draft"
        row.version += 1
        revision(session, row, "restore", {"node_id": str(row.id)})
        draft = session.get(CurriculumDraft, row.id)
        if draft is not None:
            rebase_state_only_draft(session, row, draft)
        return {"id": str(row.id), "state": row.state,
                "version": row.version, "revision": row.revision}


@router.get("/admin/curricula/{curriculum_id}/revisions")
def admin_revisions(request: Request, curriculum_id: UUID, _: Admin,
                    offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)):
    with db(request).session() as session:
        curriculum_or_404(session, curriculum_id, published=False)
        rows = session.scalars(select(CurriculumRevision).where(
            CurriculumRevision.curriculum_id == curriculum_id
        ).order_by(CurriculumRevision.number.desc()).offset(offset).limit(limit + 1)).all()
        return {"items": [{"number": row.number, "change_kind": row.change_kind,
                           "details": row.details, "created_at": row.created_at.isoformat()}
                          for row in rows[:limit]],
                "next_offset": offset + limit if len(rows) > limit else None}


@router.get("/admin/curricula/{curriculum_id}/tree")
def admin_tree(request: Request, curriculum_id: UUID, _: Admin):
    with db(request).session() as session, session.begin():
        return draft_tree(session, curriculum_or_404(
            session, curriculum_id, published=False))

KIND = {"level": (Level, Curriculum, "curriculum_id"),
        "subject": (Subject, Level, "level_id"),
        "domain": (Domain, Subject, "subject_id"),
        "category": (Category, Domain, "domain_id"),
        "topic": (Topic, Domain, "domain_id"),
        "subtopic": (Subtopic, Topic, "topic_id")}


@router.post("/admin/curriculum/curriculum/{curriculum_id}/publish")
def publish(request: Request, curriculum_id: UUID, body: PublishDraftBody, _: Admin):
    with db(request).session() as session, session.begin():
        curriculum = curriculum_or_404(session, curriculum_id, published=False, lock=True)
        return publish_draft(
            session, curriculum, body.expected_version,
            body.expected_draft_revision)

@router.patch("/admin/curriculum/{kind}/{node_id}")
def edit_node(request: Request, kind: str, node_id: UUID, body: EditBody, _: Admin):
    if kind != "curriculum" and kind not in KIND:
        fail(404, "unknown_kind")
    try:
        with db(request).session() as session, session.begin():
            if kind == "curriculum":
                node = curriculum = curriculum_or_404(session, node_id, published=False, lock=True)
            else:
                node, curriculum = ancestor_curriculum(session, kind, node_id)
                if node.archived:
                    fail(409, "node_archived")
            if node.version != body.expected_version:
                fail(409, "version_conflict")
            before = {"name": node.name}
            if kind == "curriculum":
                before["description"] = node.description
            if kind == "topic":
                before["learning_outcome"] = node.learning_outcome
            if body.name is not None:
                node.name = body.name
                if kind != "curriculum":
                    node.normalized_name = match_key(body.name)
            if body.description is not None:
                if kind != "curriculum":
                    fail(422, "description_only_for_curriculum")
                node.description = body.description
            if body.learning_outcome is not None:
                if kind != "topic":
                    fail(422, "outcome_only_for_topic")
                node.learning_outcome = body.learning_outcome
            if body.name is None and body.description is None and body.learning_outcome is None:
                fail(422, "empty_edit")
            node.version += 1
            after = {"name": node.name}
            if kind == "curriculum":
                after["description"] = node.description
            if kind == "topic":
                after["learning_outcome"] = node.learning_outcome
            revision(session, curriculum, "edit_" + kind,
                     {"node_id": str(node.id), "before": before, "after": after})
            result = {"id": str(node.id), "version": node.version, "revision": curriculum.revision}
        return result
    except IntegrityError:
        fail(409, "duplicate_sibling")


@router.post("/admin/curriculum/{kind}/{node_id}/archive")
def archive_node(request: Request, kind: str, node_id: UUID, body: VersionBody, _: Admin):
    if kind != "curriculum" and kind not in KIND:
        fail(404, "unknown_kind")
    with db(request).session() as session, session.begin():
        if kind == "curriculum":
            node = curriculum = curriculum_or_404(session, node_id, published=False, lock=True)
        else:
            node, curriculum = ancestor_curriculum(session, kind, node_id)
        if node.version != body.expected_version:
            fail(409, "version_conflict")
        if kind == "curriculum":
            curriculum.state = "archived"
        else:
            if kind == "subtopic" and curriculum.state == "published":
                siblings = session.scalars(select(Subtopic).where(
                    Subtopic.topic_id == node.topic_id, Subtopic.archived.is_(False)
                )).all()
                if len(siblings) <= 1:
                    fail(422, "published_topic_requires_subtopic")
            if node.archived:
                fail(409, "already_archived")
            node.archived = True
        node.version += 1
        revision(session, curriculum, "archive_" + kind,
                 {"node_id": str(node.id), "name": node.name})
        return {"id": str(node.id), "version": node.version, "revision": curriculum.revision,
                "archived": True}


@router.delete("/admin/curriculum/{kind}/{node_id}")
def delete_unused_node(request: Request, kind: str, node_id: UUID, body: VersionBody, _: Admin):
    if kind not in KIND:
        fail(404, "unknown_kind")
    try:
        with db(request).session() as session, session.begin():
            node, curriculum = ancestor_curriculum(session, kind, node_id)
            if curriculum.state != "draft":
                fail(409, "node_in_use")
            if node.version != body.expected_version:
                fail(409, "version_conflict")
            if node.archived:
                fail(409, "node_archived")
            node_name = node.name
            session.delete(node)
            session.flush()
            revision(session, curriculum, "delete_" + kind,
                     {"node_id": str(node_id), "name": node_name})
        return {"id": str(node_id), "status": "deleted"}
    except IntegrityError:
        fail(409, "node_in_use")


@router.get("/me/learning")
def my_learning(request: Request, principal: Member):
    with db(request).session() as session:
        rows = session.scalars(select(LearningMembership).where(
            LearningMembership.student_id == UUID(principal["id"])
        ).order_by(LearningMembership.created_at, LearningMembership.id)).all()
        return {"items": [membership_data(row) for row in rows]}


@router.post("/me/learning")
def add_learning(request: Request, body: LearningAdd, principal: Member):
    student_id = UUID(principal["id"])
    try:
        with db(request).session() as session, session.begin():
            session.execute(select(StudentProfile).where(StudentProfile.id == student_id).with_for_update()).scalar_one()
            subject_path(session, body.curriculum_id, body.level_id, body.subject_id,
                         body.domain_id, body.category_id, body.topic_id, body.subtopic_id)
            rows = session.scalars(select(LearningMembership).where(
                LearningMembership.student_id == student_id,
                LearningMembership.curriculum_id == body.curriculum_id
            )).all()
            exact = next((row for row in rows if all(
                getattr(row, field) == getattr(body, field) for field in
                ("level_id", "subject_id", "domain_id", "category_id", "topic_id", "subtopic_id")
            )), None)
            if exact:
                if not exact.visible:
                    exact.visible = True
                    exact.version += 1
                row = exact
            else:
                row = LearningMembership(student_id=student_id, curriculum_id=body.curriculum_id,
                                         level_id=body.level_id, subject_id=body.subject_id,
                                         domain_id=body.domain_id, category_id=body.category_id,
                                         topic_id=body.topic_id, subtopic_id=body.subtopic_id)
                session.add(row)
                session.flush()
            result = membership_data(row)
        return result
    except IntegrityError:
        fail(409, "membership_conflict_retry")


@router.patch("/me/learning/{membership_id}")
def set_learning_visibility(request: Request, membership_id: UUID, body: VisibilityBody, principal: Member):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(LearningMembership).where(
            LearningMembership.id == membership_id,
            LearningMembership.student_id == UUID(principal["id"])
        ).with_for_update())
        if row is None:
            fail(404, "membership_not_found")
        if (row.level_id is not None and row.subject_id is None) or row.domain_id is not None:
            fail(422, "only_curriculum_or_subject_can_hide")
        if row.version != body.expected_version:
            fail(409, "version_conflict")
        if body.visible:
            subject_path(session, row.curriculum_id, row.level_id, row.subject_id,
                         row.domain_id, row.category_id, row.topic_id, row.subtopic_id)
        if row.visible != body.visible:
            row.visible = body.visible
            row.version += 1
        return membership_data(row)


@router.get("/admin/students")
def students(request: Request, _: Admin, q: str = Query("", max_length=320),
             offset: int = Query(0, ge=0), limit: int = Query(25, ge=1, le=100)):
    with db(request).session() as session:
        query = select(StudentProfile).outerjoin(
            AdminRole, AdminRole.auth_subject == StudentProfile.auth_subject
        ).where(AdminRole.auth_subject.is_(None), StudentProfile.status.in_(["active", "pending"]))
        if q.strip():
            term = "%" + q.strip() + "%"
            filters = [StudentProfile.display_name.ilike(term), StudentProfile.email.ilike(term)]
            try:
                filters.append(StudentProfile.id == UUID(q.strip()))
            except ValueError:
                pass
            query = query.where(or_(*filters))
        total = session.scalar(select(func.count()).select_from(query.subquery()))
        rows = session.scalars(query.order_by(StudentProfile.created_at.desc(), StudentProfile.id)
                               .offset(offset).limit(limit)).all()
        return {"items": [{"id": str(p.id), "display_name": p.display_name, "email": p.email,
                           "status": p.status, "created_at": p.created_at.isoformat()} for p in rows],
                "total": total}


@router.get("/admin/students/{student_id}")
def student_detail(request: Request, student_id: UUID, _: Admin):
    with db(request).session() as session:
        profile = session.get(StudentProfile, student_id)
        if profile is None or profile.status not in ("active", "pending") or session.get(AdminRole, profile.auth_subject) is not None:
            fail(404, "student_not_found")
        learning = session.scalars(select(LearningMembership).where(
            LearningMembership.student_id == student_id
        ).order_by(LearningMembership.created_at)).all()
        return {"id": str(profile.id), "display_name": profile.display_name, "email": profile.email,
                "status": profile.status, "created_at": profile.created_at.isoformat(),
                "learning": [membership_data(row) for row in learning]}


@router.post("/admin/curriculum/imports", status_code=201)
async def upload_import(request: Request, _: Admin, curriculum_id: UUID, filename: str | None = None):
    # Bound ordinary multipart requests before parsing the body.
    length = request.headers.get("content-length")
    if length:
        try:
            if int(length) > MAX_FILE_BYTES + 1024 * 1024:
                fail(413, "file_too_large")
        except ValueError:
            fail(400, "invalid_content_length")
    if request.headers.get("content-type", "").startswith("multipart/form-data"):
        form = await request.form()
        uploaded = form.get("file")
        if uploaded is None or not hasattr(uploaded, "read"):
            fail(422, "file_required")
        filename = uploaded.filename
        payload = await uploaded.read(MAX_FILE_BYTES + 1)
    else:
        payload = await request.body()
    if len(payload) > MAX_FILE_BYTES:
        fail(413, "file_too_large")
    with db(request).session() as session:
        owner = profile_subject(session, _)
    try:
        return importer(request).upload(owner=owner, curriculum_id=curriculum_id,
                                        filename=filename or "", payload=payload)
    except (ImportFailure, WorkbookRejected) as exc:
        import_error(exc)


@router.post("/admin/curriculum/imports/{import_id}/cancel")
def cancel_import(request: Request, import_id: UUID, admin: Admin):
    with db(request).session() as session:
        owner = profile_subject(session, admin)
    try:
        return importer(request).cancel(owner=owner, import_id=import_id)
    except ImportFailure as exc:
        import_error(exc)


@router.post("/admin/curriculum/imports/{import_id}/preview")
def preview_import(request: Request, import_id: UUID, body: PreviewBody, principal: Admin):
    with db(request).session() as session:
        owner = profile_subject(session, principal)
    try:
        return importer(request).preview(owner=owner, import_id=import_id, sheet_levels=body.sheet_levels)
    except (ImportFailure, WorkbookRejected) as exc:
        importer(request).record_failure(owner=owner, import_id=import_id, operation="validation", code=exc.code)
        import_error(exc)


@router.post("/admin/curriculum/imports/{import_id}/commit")
def commit_import(request: Request, import_id: UUID, body: CommitBody, principal: Admin,
                  idempotency_key: Annotated[str | None, Header()] = None):
    with db(request).session() as session:
        owner = profile_subject(session, principal)
    try:
        return importer(request).commit(owner=owner, import_id=import_id,
                                        preview_revision=body.preview_revision,
                                        idempotency_key=idempotency_key or "", confirm=body.confirm)
    except (ImportFailure, WorkbookRejected) as exc:
        importer(request).record_failure(owner=owner, import_id=import_id, operation="replacement", code=exc.code)
        import_error(exc)


@router.get("/admin/curriculum/imports")
def import_history(request: Request, principal: Admin, curriculum_id: UUID,
                   limit: int = Query(25, ge=1, le=100), cursor: str | None = None):
    with db(request).session() as session:
        owner = profile_subject(session, principal)
    try:
        return importer(request).history(owner=owner, curriculum_id=curriculum_id, limit=limit, cursor=cursor)
    except ImportFailure as exc:
        import_error(exc)


@router.get("/admin/curriculum/imports/{import_id}")
def import_detail(request: Request, import_id: UUID, principal: Admin):
    with db(request).session() as session:
        owner = profile_subject(session, principal)
    try:
        return importer(request).detail(owner=owner, import_id=import_id)
    except ImportFailure as exc:
        import_error(exc)


@router.get("/admin/curriculum/imports/{import_id}/rows")
def import_rows(request: Request, import_id: UUID, principal: Admin,
                offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100)):
    with db(request).session() as session:
        owner = profile_subject(session, principal)
    try:
        return importer(request).row_page(owner=owner, import_id=import_id, offset=offset, limit=limit)
    except ImportFailure as exc:
        import_error(exc)


@router.get("/admin/curriculum/imports/{import_id}/source-rows")
def import_source_rows(request: Request, import_id: UUID, principal: Admin,
                       offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100)):
    with db(request).session() as session:
        owner = profile_subject(session, principal)
    try:
        return importer(request).source_page(owner=owner, import_id=import_id,
                                             offset=offset, limit=limit)
    except (ImportFailure, WorkbookRejected) as exc:
        import_error(exc)


@router.get("/admin/curriculum/imports/{import_id}/review-rows")
def import_review_rows(request: Request, import_id: UUID, principal: Admin,
                       offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100),
                       operation: str = Query("", max_length=16), q: str = Query("", max_length=255)):
    with db(request).session() as session:
        owner = profile_subject(session, principal)
    try:
        return importer(request).review_page(owner=owner, import_id=import_id,
                                              offset=offset, limit=limit, operation=operation, q=q)
    except (ImportFailure, WorkbookRejected) as exc:
        import_error(exc)


@router.post("/admin/curriculum/imports/{import_id}/review")
def review_import_changes(request: Request, import_id: UUID, body: ReviewChangesBody,
                          principal: Admin):
    with db(request).session() as session:
        owner = profile_subject(session, principal)
    try:
        return importer(request).review_changes(
            owner=owner, import_id=import_id, preview_revision=body.preview_revision,
            changes=[change.model_dump() for change in body.changes])
    except (ImportFailure, WorkbookRejected) as exc:
        importer(request).record_failure(owner=owner, import_id=import_id, operation="corrections", code=exc.code)
        import_error(exc)


@router.get("/admin/curriculum/imports/{import_id}/issues")
def import_issues(request: Request, import_id: UUID, principal: Admin,
                  offset: int = Query(0, ge=0), limit: int = Query(100, ge=1, le=100)):
    with db(request).session() as session:
        owner = profile_subject(session, principal)
    try:
        return importer(request).issue_page(owner=owner, import_id=import_id, offset=offset, limit=limit)
    except ImportFailure as exc:
        import_error(exc)

@router.post("/admin/curriculum/{kind}", status_code=201)
def create_child(request: Request, kind: str, body: ChildCreate, _: Admin):
    if kind not in KIND:
        fail(404, "unknown_kind")
    cls, parent_cls, parent_field = KIND[kind]
    if kind != "topic" and (body.learning_outcome is not None or body.subtopic_name is not None):
        fail(422, "topic_fields_only_for_topic")
    try:
        with db(request).session() as session, session.begin():
            parent = session.get(parent_cls, body.parent_id)
            if parent is None or getattr(parent, "archived", False):
                fail(404, "parent_not_found")
            if isinstance(parent, Curriculum):
                curriculum = curriculum_or_404(session, parent.id, published=False, lock=True)
            else:
                _, curriculum = ancestor_curriculum(session, {v[0]: k for k, v in KIND.items()}[parent_cls], parent.id)
            if curriculum.state == "archived":
                fail(409, "curriculum_archived")
            if kind == "topic" and curriculum.state == "published" and not body.subtopic_name:
                fail(422, "published_topic_requires_subtopic")
            if kind == "topic" and body.category_id is not None:
                category = session.get(Category, body.category_id)
                if category is None or category.archived or category.domain_id != parent.id:
                    fail(422, "invalid_category_path")
            elif body.category_id is not None:
                fail(422, "category_only_for_topic")
            order = body.display_order
            if order is None:
                maximum = session.scalar(select(func.max(cls.display_order)).where(getattr(cls, parent_field) == parent.id))
                order = 0 if maximum is None else maximum + 1
            fields = {parent_field: parent.id, "name": body.name, "normalized_name": match_key(body.name),
                      "display_order": order}
            if kind == "level":
                fields.update(code=body.name[:80], normalized_code=match_key(body.name[:80]))
            if kind == "topic":
                fields.update(category_id=body.category_id, learning_outcome=body.learning_outcome)
            node = cls(**fields)
            session.add(node)
            session.flush()
            if kind == "topic" and body.subtopic_name:
                session.add(Subtopic(topic_id=node.id, name=body.subtopic_name.strip(),
                                     normalized_name=match_key(body.subtopic_name)))
            revision(session, curriculum, "create_" + kind,
                     {"node_id": str(node.id), "name": node.name,
                      "parent_id": str(parent.id)})
            result = {"id": str(node.id), "name": node.name, "version": node.version,
                      "curriculum_id": str(curriculum.id), "revision": curriculum.revision}
        return result
    except IntegrityError:
        fail(409, "duplicate_sibling")









