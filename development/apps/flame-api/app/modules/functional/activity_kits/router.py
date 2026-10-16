"""Admin multi-topic activity kit catalogue. No checkout or member recommendations."""
from app.contracts.learning_metadata import LearningMetadata, metadata_data
from decimal import Decimal
from typing import Annotated
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import delete, func, or_, select

from app.modules.functional.activity_kits.models import ActivityKit, KitTopic
from app.modules.functional.activity_kits.service import publication_check
from app.modules.functional.identity.dependencies import require_admin
from app.modules.functional.identity.models import StudentProfile
from app.modules.functional.resources.models import ResourceUpload
from app.modules.functional.resources.service import fail, path_info
from app.modules.functional.resources.storage import ResourceStorage, StorageUnavailable
from app.modules.functional.resources.validation import MediaRejected, validate_external_url

router = APIRouter(prefix="/api/v1/admin/activity-kits", tags=["admin-activity-kits"])
Admin = Annotated[dict, Depends(require_admin)]


class KitPath(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_id: UUID
    subtopic_id: UUID | None = None


class KitDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learning_metadata: LearningMetadata = Field(default_factory=LearningMetadata)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    image_upload_ids: list[UUID] = Field(default_factory=list, max_length=5)
    materials: list[str] = Field(default_factory=list, max_length=100)
    instructions: str | None = Field(default=None, max_length=10000)
    supervision: str | None = Field(default=None, max_length=4000)
    cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    availability: str | None = Field(default=None, max_length=255)
    supplier_url: str | None = Field(default=None, max_length=2048)
    paths: list[KitPath] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate(self):
        if not self.name.strip() or (self.cost is None) != (self.currency is None):
            raise ValueError("invalid_kit_metadata")
        if any(not item.strip() or len(item) > 500 for item in self.materials):
            raise ValueError("invalid_kit_material")
        if len(set(self.image_upload_ids)) != len(self.image_upload_ids):
            raise ValueError("duplicate_kit_image")
        if len({(p.topic_id, p.subtopic_id) for p in self.paths}) != len(self.paths):
            raise ValueError("duplicate_kit_path")
        return self


class KitEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learning_metadata: LearningMetadata | None = None
    expected_version: int = Field(ge=1)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    image_upload_ids: list[UUID] | None = Field(default=None, max_length=5)
    materials: list[str] | None = Field(default=None, max_length=100)
    instructions: str | None = Field(default=None, max_length=10000)
    supervision: str | None = Field(default=None, max_length=4000)
    cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    availability: str | None = Field(default=None, max_length=255)
    supplier_url: str | None = Field(default=None, max_length=2048)
    paths: list[KitPath] | None = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate(self):
        if self.name is not None and not self.name.strip():
            raise ValueError("kit_name_required")
        if self.materials is not None and any(not item.strip() or len(item) > 500 for item in self.materials):
            raise ValueError("invalid_kit_material")
        if self.image_upload_ids is not None and len(set(self.image_upload_ids)) != len(self.image_upload_ids):
            raise ValueError("duplicate_kit_image")
        if self.paths is not None and len({(p.topic_id, p.subtopic_id) for p in self.paths}) != len(self.paths):
            raise ValueError("duplicate_kit_path")
        return self


class VersionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


def db(request):
    return request.app.state.database


def supplier(raw: str | None):
    if not raw:
        return None
    try:
        host = urlsplit(raw).hostname or ""
        return validate_external_url(raw, {host.lower().rstrip(".")})
    except (MediaRejected, ValueError) as exc:
        fail(422, str(exc))


def kit_data(session, row):
    paths = session.scalars(select(KitTopic).where(KitTopic.kit_id == row.id)).all()
    images = session.scalars(select(ResourceUpload).where(ResourceUpload.kit_id == row.id)).all()
    return {"learning_metadata": metadata_data(row.learning_metadata), "id": str(row.id), "name": row.name, "description": row.description,
            "image_upload_ids": [str(item.id) for item in images if item.storage_key in row.image_keys],
            "materials": row.materials, "instructions": row.instructions, "supervision": row.supervision,
            "cost": str(row.cost) if row.cost is not None else None, "currency": row.currency,
            "availability": row.availability, "supplier_url": row.supplier_url,
            "published": row.published, "version": row.version,
            "paths": [{"topic_id": str(p.topic_id),
                       "subtopic_id": str(p.subtopic_id) if p.subtopic_id else None} for p in paths]}


def replace_paths(session, row, paths):
    for path in paths:
        path_info(session, path.topic_id, path.subtopic_id)
    session.execute(delete(KitTopic).where(KitTopic.kit_id == row.id))
    session.flush()
    for path in paths:
        session.add(KitTopic(kit_id=row.id, topic_id=path.topic_id, subtopic_id=path.subtopic_id))


def replace_images(session, row, upload_ids, auth_subject):
    uploads = []
    for upload_id in upload_ids:
        upload = session.scalar(select(ResourceUpload).where(ResourceUpload.id == upload_id).with_for_update())
        if upload is None or upload.owner_auth_subject != auth_subject:
            fail(404, "upload_not_found")
        if upload.media_type != "image":
            fail(422, "kit_image_required")
        if upload.resource_id is not None or upload.kit_id not in (None, row.id):
            fail(409, "upload_already_used")
        uploads.append(upload)
    row.image_keys = [upload.storage_key for upload in uploads]
    for upload in uploads:
        upload.kit_id = row.id


@router.get("")
def list_kits(request: Request, _: Admin, q: str = Query("", max_length=255),
              published: bool | None = None, topic_id: UUID | None = None,
              offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    with db(request).session() as session:
        query = select(ActivityKit)
        if q.strip():
            query = query.where(or_(ActivityKit.name.ilike("%" + q.strip() + "%"),
                                    ActivityKit.description.ilike("%" + q.strip() + "%")))
        if published is not None:
            query = query.where(ActivityKit.published == published)
        if topic_id:
            query = query.where(ActivityKit.id.in_(select(KitTopic.kit_id).where(KitTopic.topic_id == topic_id)))
        total = session.scalar(select(func.count()).select_from(query.subquery()))
        rows = session.scalars(query.order_by(ActivityKit.name, ActivityKit.id).offset(offset).limit(limit)).all()
        return {"items": [kit_data(session, row) for row in rows], "total": total,
                "offset": offset, "limit": limit}


@router.post("", status_code=201)
def create_kit(request: Request, principal: Admin, body: KitDraft):
    with db(request).session() as session, session.begin():
        profile = session.get(StudentProfile, UUID(principal["id"]))
        if profile is None:
            fail(401, "profile_not_found")
        row = ActivityKit(name=body.name.strip(), learning_metadata=metadata_data(body.learning_metadata), description=body.description,
                          materials=body.materials, instructions=body.instructions,
                          supervision=body.supervision, cost=body.cost, currency=body.currency,
                          availability=body.availability, supplier_url=supplier(body.supplier_url))
        session.add(row)
        session.flush()
        replace_paths(session, row, body.paths)
        replace_images(session, row, body.image_upload_ids, profile.auth_subject)
        session.flush()
        result = kit_data(session, row)
    return result


@router.get("/{kit_id}")
def kit_detail(request: Request, _: Admin, kit_id: UUID):
    with db(request).session() as session:
        row = session.get(ActivityKit, kit_id)
        if row is None:
            fail(404, "kit_not_found")
        return kit_data(session, row)


@router.patch("/{kit_id}")
def edit_kit(request: Request, principal: Admin, kit_id: UUID, body: KitEdit):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(ActivityKit).where(ActivityKit.id == kit_id).with_for_update())
        if row is None:
            fail(404, "kit_not_found")
        if row.version != body.expected_version:
            fail(409, "stale_version")
        profile = session.get(StudentProfile, UUID(principal["id"]))
        if profile is None:
            fail(401, "profile_not_found")
        if "learning_metadata" in body.model_fields_set:
            if body.learning_metadata is None:
                fail(422, "learning_metadata_required")
            row.learning_metadata = metadata_data(body.learning_metadata)
        for field in ("name", "description", "materials", "instructions", "supervision",
                      "cost", "currency", "availability"):
            if field in body.model_fields_set:
                setattr(row, field, getattr(body, field))
        if "supplier_url" in body.model_fields_set:
            row.supplier_url = supplier(body.supplier_url)
        if (row.cost is None) != (row.currency is None):
            fail(422, "cost_currency_together")
        if body.paths is not None:
            replace_paths(session, row, body.paths)
        if body.image_upload_ids is not None:
            replace_images(session, row, body.image_upload_ids, profile.auth_subject)
        row.version += 1
        session.flush()
        if row.published:
            publication_check(session, row, request.app.state.settings)
        result = kit_data(session, row)
    return result


@router.post("/{kit_id}/publish")
def publish_kit(request: Request, _: Admin, kit_id: UUID, body: VersionBody):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(ActivityKit).where(ActivityKit.id == kit_id).with_for_update())
        if row is None:
            fail(404, "kit_not_found")
        if row.version != body.expected_version:
            fail(409, "stale_version")
        publication_check(session, row, request.app.state.settings)
        row.published = True
        row.version += 1
        session.flush()
        result = kit_data(session, row)
    return result


@router.post("/{kit_id}/unpublish")
def unpublish_kit(request: Request, _: Admin, kit_id: UUID, body: VersionBody):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(ActivityKit).where(ActivityKit.id == kit_id).with_for_update())
        if row is None:
            fail(404, "kit_not_found")
        if row.version != body.expected_version:
            fail(409, "stale_version")
        row.published = False
        row.version += 1
        session.flush()
        result = kit_data(session, row)
    return result
