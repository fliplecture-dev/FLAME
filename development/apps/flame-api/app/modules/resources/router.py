"""Admin-only B9.2 resource upload and draft creation."""
from app.contracts.learning_metadata import LearningMetadata, metadata_data
from datetime import datetime, timezone
from pathlib import Path
from time import time
from tempfile import TemporaryDirectory
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from sqlalchemy import delete, func, or_, select, text

from app.modules.curriculum.catalogue import ancestor_curriculum
from app.modules.curriculum.models import Curriculum, Level, Subject, Domain, Category, Topic, Subtopic
from app.modules.identity.dependencies import require_admin
from app.modules.identity.models import StudentProfile
from app.modules.resources.models import Resource, ResourceTopic, ResourceUpload
from app.modules.recommendations.repository import resource_reference_count
from app.modules.activity_kits.models import ActivityKit
from app.modules.student_activity.models import ActivityEvent
from app.modules.resources.service import admin_data, path_info, path_choices, publication_check, validate_resource_paths
from app.modules.resources.storage import ResourceStorage, StorageUnavailable
from app.modules.resources.validation import FORMATS, MEDIA_TYPES, RESOURCE_TYPES, MediaRejected, declared_format, inspect_media, validate_external_url, canonical_type
from app.modules.resources.external_video import inspect_video, video_data, embed_url, is_provider_url, reject as video_reject

router = APIRouter(prefix="/api/v1/admin/resources", tags=["admin-resources"])
Admin = Annotated[dict, Depends(require_admin)]


class ResourcePath(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_id: UUID
    subtopic_id: UUID | None = None


class DraftCreate(BaseModel):
    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        return canonical_type(value)

    model_config = ConfigDict(extra="forbid")
    learning_metadata: LearningMetadata = Field(default_factory=LearningMetadata)
    type: str
    creation_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    upload_id: UUID | None = None
    thumbnail_upload_id: UUID | None = None
    external_url: str | None = Field(default=None, max_length=2048)
    paths: list[ResourcePath] = Field(default_factory=list, max_length=10000)
    alt_text: str | None = Field(default=None, max_length=1000)
    caption_or_transcript: str | None = Field(default=None, max_length=10000)
    accessibility_note: str | None = Field(default=None, max_length=1000)
    availability: str = "available"
    rights_basis: str | None = None
    rights_holder: str | None = Field(default=None, max_length=255)
    rights_reference: str | None = Field(default=None, max_length=2048)
    attribution: str | None = Field(default=None, max_length=2000)
    distribution_scope: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value):
        if not value.strip():
            raise ValueError("title_required")
        return value.strip()

    @model_validator(mode="after")
    def check_source_and_type(self):
        if self.type not in RESOURCE_TYPES or self.availability not in ("available", "unavailable") or self.rights_basis not in (None, "owned", "licensed", "permission"):
            raise ValueError("invalid_resource_metadata")
        if bool(self.upload_id) == bool(self.external_url) and not (self.type=="interactive" and not self.upload_id and not self.external_url):
            raise ValueError("one_media_source_required")
        if len({(p.topic_id, p.subtopic_id) for p in self.paths}) != len(self.paths):
            raise ValueError("duplicate_resource_path")
        return self


def fail(status, code):
    raise HTTPException(status, code)


def db(request):
    return request.app.state.database


def settings(request):
    return request.app.state.settings


class VideoInspect(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str = Field(min_length=1, max_length=2048)


@router.post("/external-video/inspect")
def inspect_external_video(request: Request, _: Admin, body: VideoInspect):
    return inspect_video(body.url, settings(request))


@router.post("/uploads", status_code=201)
def upload_resource(request: Request, _: Admin, file: UploadFile = File(...)):
    return store_upload(request, _, file)


def store_upload(request, principal, file, *, reserved_id=None):
    """Validate bytes before storage; direct-transfer retries reuse a server-reserved ID."""
    with db(request).session() as session:
        profile = session.get(StudentProfile, UUID(principal["id"]))
        if profile is None:
            fail(401, "profile_not_found")
        owner = profile.auth_subject
        if reserved_id:
            existing = session.get(ResourceUpload, reserved_id)
            if existing:
                if existing.owner_auth_subject != owner:
                    fail(404, "upload_not_found")
                return {"upload_id": str(existing.id), "mime_type": existing.mime_type,
                        "byte_size": existing.byte_size, "media_type": existing.media_type}
    try:
        suffix, mime_type, media_type, limit = declared_format(file.filename or "", file.content_type or "")
    except MediaRejected as exc:
        fail(422, str(exc))
    storage = ResourceStorage(settings(request))
    with TemporaryDirectory() as temp_dir:
        temp = Path(temp_dir) / "upload"
        size = 0
        with temp.open("wb") as out:
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > limit:
                    fail(413, "file_too_large")
                out.write(chunk)
        if size == 0:
            fail(422, "empty_file")
        try:
            inspect_media(temp, mime_type)
        except MediaRejected as exc:
            fail(422, str(exc))
        key = "resource-uploads/" + reserved_id.hex + suffix if reserved_id else storage.new_key(suffix)
        try:
            if reserved_id and storage.exists(key):
                # An interrupted finalizer may have stored bytes before committing its row.
                import hashlib
                restored = Path(temp_dir) / "existing"
                storage.download_to(key, restored, limit)
                with temp.open("rb") as first, restored.open("rb") as second:
                    if hashlib.file_digest(first, "sha256").digest() != hashlib.file_digest(second, "sha256").digest():
                        fail(409, "upload_content_conflict")
            else:
                storage.put(key, temp, mime_type)
        except StorageUnavailable:
            fail(503, "resource_storage_unavailable")
    try:
        with db(request).session() as session, session.begin():
            profile = session.get(StudentProfile, UUID(principal["id"]))
            if profile is None:
                fail(401, "profile_not_found")
            row = ResourceUpload(storage_key=key, owner_auth_subject=profile.auth_subject,
                                 mime_type=mime_type, byte_size=size, media_type=media_type,
                                 file_name=Path((file.filename or "media").replace("\\", "/")).name[:255])
            if reserved_id:
                row.id = reserved_id
            session.add(row)
            session.flush()
            result = {"upload_id": str(row.id), "mime_type": mime_type, "byte_size": size,
                      "media_type": media_type}
    except Exception:
        if not reserved_id:
            storage.delete(key)
        raise
    return result


@router.post("", status_code=201)
def create_resource(request: Request, _: Admin, body: DraftCreate):
    config = settings(request)
    external_url = None
    external_video = None
    if body.type != "video" and is_provider_url(body.external_url): video_reject("external_video_type_required")
    if body.type == "video" and is_provider_url(body.external_url):
        if not body.external_url or body.upload_id: video_reject("external_video_url_invalid")
        external_video = inspect_video(body.external_url, config)
        external_url = external_video["canonical_url"]
    if body.external_url:
        allowed = {host.strip().lower() for host in config.resource_allowed_hosts.split(",") if host.strip()}
        try:
            if external_video is None: external_url = validate_external_url(body.external_url, allowed)
        except MediaRejected as exc:
            fail(422, str(exc))
    with db(request).session() as session, session.begin():
        profile = session.get(StudentProfile, UUID(_["id"]))
        if profile is None:
            fail(401, "profile_not_found")
        if body.creation_id:
            # Serialize retries for the same client-generated creation identity.
            session.execute(text("SELECT pg_advisory_xact_lock(:key)"),
                            {"key": body.creation_id.int % (2**63 - 1)})
            existing = session.get(Resource, body.creation_id)
            if existing is not None:
                # Never overwrite a concurrent edit or create a second resource.
                fail(409, "resource_creation_exists")
        upload = None
        if body.upload_id:
            upload = session.scalar(select(ResourceUpload).where(ResourceUpload.id == body.upload_id).with_for_update())
            if upload is None or upload.owner_auth_subject != profile.auth_subject:
                fail(404, "upload_not_found")
            if upload.resource_id is not None or upload.kit_id is not None:
                fail(409, "upload_already_used")
            if upload.media_type not in MEDIA_TYPES[body.type]:
                fail(422, "resource_type_media_mismatch")
        validate_resource_paths(session, body.paths)
        paths = body.paths
        row = Resource(type=body.type, learning_metadata=metadata_data(body.learning_metadata), title=body.title, description=body.description,
                       storage_key=upload.storage_key if upload else None, external_url=external_url,
                       external_video=external_video,
                       mime_type=upload.mime_type if upload else None,
                       byte_size=upload.byte_size if upload else None,
                       alt_text=body.alt_text, caption_or_transcript=body.caption_or_transcript,
                       accessibility_note=body.accessibility_note, availability=body.availability,
                       rights_basis=body.rights_basis, rights_holder=body.rights_holder,
                       rights_reference=body.rights_reference, attribution=body.attribution,
                       distribution_scope=body.distribution_scope)
        if body.creation_id:
            row.id = body.creation_id
        session.add(row)
        session.flush()
        if body.thumbnail_upload_id:
            from app.modules.resources.thumbnails import assign_thumbnail
            assign_thumbnail(session, row, body.thumbnail_upload_id, profile.auth_subject)
        for path in paths:
            session.add(ResourceTopic(resource_id=row.id, topic_id=path.topic_id, subtopic_id=path.subtopic_id))
        if upload:
            upload.resource_id = row.id
        session.flush()
        result = admin_data(session, row)
    return result


class DraftEdit(BaseModel):
    @field_validator("type", mode="before")
    @classmethod
    def normalize_type(cls, value):
        return canonical_type(value)

    model_config = ConfigDict(extra="forbid")
    learning_metadata: LearningMetadata | None = None
    expected_version: int = Field(ge=1)
    type: str | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    upload_id: UUID | None = None
    thumbnail_upload_id: UUID | None = None
    external_url: str | None = Field(default=None, max_length=2048)
    paths: list[ResourcePath] | None = Field(default=None, max_length=10000)
    alt_text: str | None = Field(default=None, max_length=1000)
    caption_or_transcript: str | None = Field(default=None, max_length=10000)
    accessibility_note: str | None = Field(default=None, max_length=1000)
    availability: str | None = None
    rights_basis: str | None = None
    rights_holder: str | None = Field(default=None, max_length=255)
    rights_reference: str | None = Field(default=None, max_length=2048)
    attribution: str | None = Field(default=None, max_length=2000)
    distribution_scope: str | None = Field(default=None, max_length=255)

    @model_validator(mode="after")
    def validate_edit(self):
        if self.type is not None and self.type not in RESOURCE_TYPES:
            raise ValueError("invalid_resource_type")
        if self.availability is not None and self.availability not in ("available", "unavailable"):
            raise ValueError("invalid_resource_availability")
        if self.rights_basis is not None and self.rights_basis not in ("owned", "licensed", "permission"):
            raise ValueError("invalid_rights_basis")
        if "upload_id" in self.model_fields_set and "external_url" in self.model_fields_set:
            raise ValueError("one_media_source_required")
        if self.paths is not None and len({(p.topic_id, p.subtopic_id) for p in self.paths}) != len(self.paths):
            raise ValueError("duplicate_resource_path")
        if self.title is not None and not self.title.strip():
            raise ValueError("title_required")
        return self


class VersionBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)


@router.get("")
def list_resources(request: Request, _: Admin, q: str = Query("", max_length=255),
                   topic_label: str = Query("", max_length=255),
                   type: str | None = None, published: bool | None = None, availability: str | None = None,
                   format: str | None = None, sort: str = "updated", direction: str = "desc",
                   curriculum_id: UUID | None = None, level_id: UUID | None = None, subject_id: UUID | None = None,
                   domain_id: UUID | None = None, category_id: UUID | None = None, topic_id: UUID | None = None,
                   subtopic_id: UUID | None = None,
                   offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    with db(request).session() as session:
        query = select(Resource).where(Resource.deleted_at.is_(None), Resource.type.in_(RESOURCE_TYPES))
        if q.strip():
            query = query.where(or_(Resource.title.ilike("%" + q.strip() + "%"),
                                    Resource.description.ilike("%" + q.strip() + "%")))
        if topic_label.strip():
            literal = topic_label.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(Resource.learning_metadata["topic_labels"].astext.ilike("%" + literal + "%", escape="\\"))
        if type:
            query = query.where(Resource.type == canonical_type(type))
        if published is not None:
            query = query.where(Resource.published == published)
        if availability:
            query = query.where(Resource.availability == availability)
        if format:
            mimes = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp", "GIF": "image/gif", "MP4": "video/mp4", "WEBM": "video/webm", "PDF": "application/pdf", "HTML5": "text/html"}
            if format.upper() == "URL": query = query.where(Resource.external_url.is_not(None))
            else: query = query.where(Resource.mime_type == mimes.get(format.upper(), "unsupported"))
        if any([curriculum_id, level_id, subject_id, domain_id, category_id, topic_id, subtopic_id]):
            links = (select(ResourceTopic.id).join(Topic, ResourceTopic.topic_id == Topic.id)
                     .join(Domain, Topic.domain_id == Domain.id).join(Subject, Domain.subject_id == Subject.id)
                     .join(Level, Subject.level_id == Level.id).join(Curriculum, Level.curriculum_id == Curriculum.id)
                     .outerjoin(Category, Topic.category_id == Category.id)
                     .where(ResourceTopic.resource_id == Resource.id, Curriculum.state != "archived",
                            Topic.archived.is_(False), Domain.archived.is_(False), Subject.archived.is_(False), Level.archived.is_(False),
                            or_(Topic.category_id.is_(None), Category.archived.is_(False))))
            # Require a valid current direct link even when a higher ancestor is selected.
            valid_leaf = select(Subtopic.id).where(Subtopic.id == ResourceTopic.subtopic_id, Subtopic.topic_id == Topic.id, Subtopic.archived.is_(False)).correlate(ResourceTopic, Topic).exists()
            links = links.where(or_(ResourceTopic.subtopic_id.is_(None), valid_leaf))
            for value, column in [(curriculum_id, Curriculum.id), (level_id, Level.id), (subject_id, Subject.id), (domain_id, Domain.id), (category_id, Topic.category_id), (topic_id, Topic.id)]:
                if value: links = links.where(column == value)
            if subtopic_id:
                covered = select(Subtopic.id).where(Subtopic.id == subtopic_id, Subtopic.topic_id == Topic.id, Subtopic.archived.is_(False)).correlate(Topic).exists()
                links = links.where(covered, or_(ResourceTopic.subtopic_id.is_(None), ResourceTopic.subtopic_id == subtopic_id))
            query = query.where(links.exists())
        order = {"title": func.lower(Resource.title), "type": Resource.type, "status": Resource.published, "updated": Resource.updated_at}.get(sort)
        if order is None or direction not in {"asc", "desc"}: fail(422, "invalid_resource_sort")
        total = session.scalar(select(func.count()).select_from(query.subquery()))
        rows = session.scalars(query.order_by(order.asc() if direction == "asc" else order.desc(), Resource.id).offset(offset).limit(limit)).all()
        return {"items": [admin_data(session, row) for row in rows], "total": total,
                "offset": offset, "limit": limit}


@router.get("/paths")
def resource_paths(request: Request, _: Admin, curriculum_id: UUID | None = None):
    with db(request).session() as session:
        ids = [curriculum_id] if curriculum_id else session.scalars(select(Curriculum.id).where(Curriculum.state != "archived")).all()
        return {"items": [choice for cid in ids for choice in path_choices(session, cid)]}


@router.get("/{resource_id}")
def resource_detail(request: Request, _: Admin, resource_id: UUID):
    with db(request).session() as session:
        row = session.get(Resource, resource_id)
        if row is None or row.deleted_at is not None:
            fail(404, "resource_not_found")
        return admin_data(session, row)


@router.patch("/{resource_id}")
def edit_resource(request: Request, _: Admin, resource_id: UUID, body: DraftEdit):
    config = settings(request)
    with db(request).session() as session, session.begin():
        row = session.scalar(select(Resource).where(Resource.id == resource_id).with_for_update())
        if row is None or row.deleted_at is not None:
            fail(404, "resource_not_found")
        if row.version != body.expected_version:
            fail(409, "stale_version")
        profile = session.get(StudentProfile, UUID(_["id"]))
        if profile is None:
            fail(401, "profile_not_found")
        upload = None
        if "upload_id" in body.model_fields_set:
            if body.upload_id is None:
                fail(422, "upload_required")
            upload = session.scalar(select(ResourceUpload).where(ResourceUpload.id == body.upload_id).with_for_update())
            if upload is None or upload.owner_auth_subject != profile.auth_subject:
                fail(404, "upload_not_found")
            if upload.resource_id is not None or upload.kit_id is not None:
                fail(409, "upload_already_used")
            if upload.media_type not in MEDIA_TYPES[body.type or row.type]:
                fail(422, "resource_type_media_mismatch")
            row.storage_key, row.external_url, row.external_video = upload.storage_key, None, None
            row.mime_type, row.byte_size = upload.mime_type, upload.byte_size
            upload.resource_id = row.id
        if "external_url" in body.model_fields_set:
            if not body.external_url:
                fail(422, "external_url_required")
            if (body.type or row.type) != "video" and is_provider_url(body.external_url): video_reject("external_video_type_required")
            allowed = {host.strip().lower() for host in config.resource_allowed_hosts.split(",") if host.strip()}
            try:
                if (body.type or row.type) == "video" and is_provider_url(body.external_url):
                    row.external_video = inspect_video(body.external_url, config)
                    row.external_url = row.external_video["canonical_url"]
                else:
                    row.external_url = validate_external_url(body.external_url, allowed)
                    row.external_video = None
            except MediaRejected as exc:
                fail(422, str(exc))
            row.storage_key, row.mime_type, row.byte_size = None, None, None
        if "learning_metadata" in body.model_fields_set:
            if body.learning_metadata is None:
                fail(422, "learning_metadata_required")
            row.learning_metadata = metadata_data(body.learning_metadata)
        for field in ("type", "title", "description", "alt_text", "caption_or_transcript",
                      "accessibility_note", "availability", "rights_basis", "rights_holder",
                      "rights_reference", "attribution", "distribution_scope"):
            if field in body.model_fields_set:
                setattr(row, field, getattr(body, field))
        if "thumbnail_upload_id" in body.model_fields_set:
            from app.modules.resources.thumbnails import assign_thumbnail
            assign_thumbnail(session, row, body.thumbnail_upload_id, profile.auth_subject)
        if row.type != "video": row.thumbnail_storage_key = None
        if row.type!="interactive" and not row.storage_key and not row.external_url: fail(422, "resource_asset_missing")
        if row.type not in RESOURCE_TYPES:
            fail(422, "invalid_resource_type")
        if row.type == "video" and is_provider_url(row.external_url) and not row.external_video:
            video_reject("external_video_url_invalid")
        if row.type != "video" or not is_provider_url(row.external_url): row.external_video = None
        if row.storage_key and row.mime_type:
            media_type = next((v[1] for v in FORMATS.values() if v[0] == row.mime_type), None)
            if media_type not in MEDIA_TYPES[row.type]:
                fail(422, "resource_type_media_mismatch")
        if body.paths is not None:
            validate_resource_paths(session, body.paths)
            session.execute(delete(ResourceTopic).where(ResourceTopic.resource_id == row.id))
            session.flush()
            for path in body.paths:
                session.add(ResourceTopic(resource_id=row.id, topic_id=path.topic_id, subtopic_id=path.subtopic_id))
        row.version += 1
        if row.published and body.model_fields_set - {"expected_version", "paths"}:
            publication_check(session, row, config)
        session.flush()
        result = admin_data(session, row)
    return result


@router.post("/{resource_id}/publish")
def publish_resource(request: Request, _: Admin, resource_id: UUID, body: VersionBody):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(Resource).where(Resource.id == resource_id).with_for_update())
        if row is None or row.deleted_at is not None:
            fail(404, "resource_not_found")
        if row.version != body.expected_version:
            fail(409, "stale_version")
        publication_check(session, row, settings(request))
        row.published = True
        row.version += 1
        session.flush()
        result = admin_data(session, row)
    return result


@router.post("/{resource_id}/unpublish")
def unpublish_resource(request: Request, _: Admin, resource_id: UUID, body: VersionBody):
    with db(request).session() as session, session.begin():
        row = session.scalar(select(Resource).where(Resource.id == resource_id).with_for_update())
        if row is None or row.deleted_at is not None:
            fail(404, "resource_not_found")
        if row.version != body.expected_version:
            fail(409, "stale_version")
        row.published = False
        row.version += 1
        session.flush()
        result = admin_data(session, row)
    return result


@router.get("/{resource_id}/preview")
def preview_resource(request: Request, _: Admin, resource_id: UUID, thumbnail: bool = False):
    config = settings(request)
    with db(request).session() as session:
        row = session.get(Resource, resource_id)
        if row is None or row.deleted_at is not None:
            fail(404, "resource_not_found")
        if row.type=="interactive" and not row.storage_key and not row.external_url:
            return {"url":"", "launch_mode":"interactive_pending", "html_document":"", "media_ready":False, "message":"Paste or upload HTML5 to preview this draft."}
        if thumbnail:
            from app.modules.resources.thumbnails import thumbnail_delivery
            return thumbnail_delivery(row, config, preview=True)
        if row.type == "interactive" and row.mime_type == "text/html":
            from app.modules.resources.interactive import interactive_data
            return interactive_data(row, ResourceStorage(config))
        if row.type == "video" and is_provider_url(row.external_url):
            return {"launch_mode": "external_video", "url": embed_url(row), "external_video": video_data(row)}
        if row.external_url:
            return {"url": row.external_url, "launch_mode": "separate_page" if row.type == "interactive" else "media"}
        if not row.storage_key:
            fail(404, "resource_asset_missing")
        storage = ResourceStorage(config)
        try:
            if not storage.exists(row.storage_key):
                fail(404, "resource_asset_missing")
            if config.resource_storage_backend == "local":
                return {"url": f"/api/b9/admin/resources/{row.id}/preview-content",
                        "launch_mode": "media"}
            expires = int(time()) + 300
            return {"url": storage.signed_url(row.id, row.storage_key, expires, ""),
                    "launch_mode": "media"}
        except StorageUnavailable:
            fail(503, "resource_delivery_unavailable")


@router.get("/{resource_id}/preview-content")
def preview_resource_content(request: Request, _: Admin, resource_id: UUID, thumbnail: bool = False):
    config = settings(request)
    if config.resource_storage_backend != "local":
        fail(404, "resource_not_found")
    with db(request).session() as session:
        row = session.get(Resource, resource_id)
        if row is None or row.deleted_at is not None:
            fail(404, "resource_not_found")
        asset_key = row.thumbnail_storage_key if thumbnail else row.storage_key
        if not asset_key: fail(404, "resource_not_found")
        if row.type == "interactive" or row.mime_type == "text/html":
            fail(404, "resource_not_found")
        try:
            key = ResourceStorage(config).checked_key(asset_key)
        except StorageUnavailable:
            fail(404, "resource_not_found")
        target = ResourceStorage(config).local_path(key)
        if not target.is_file():
            fail(404, "resource_asset_missing")
        return FileResponse(target, media_type=("image/" + ("jpeg" if key.endswith((".jpg", ".jpeg")) else key.rsplit(".", 1)[1])) if thumbnail else row.mime_type or "application/octet-stream",
                            headers={"X-Content-Type-Options": "nosniff",
                                     "Cache-Control": "private, no-store"})


class DeleteResource(VersionBody):
    confirm_resource_id: UUID


def deletion_dependencies(session, row):
    """Inspect live sharing and historical references; retained assets keep them intact."""
    rid = str(row.id)
    shared = session.scalar(select(func.count()).select_from(Resource).where(
        Resource.id != row.id, Resource.storage_key == row.storage_key)) if row.storage_key else 0
    kits = session.scalar(select(func.count()).select_from(ActivityKit).where(
        ActivityKit.image_keys.contains([row.storage_key]))) if row.storage_key else 0
    uploads = session.scalar(select(func.count()).select_from(ResourceUpload).where(ResourceUpload.resource_id == row.id))
    activity = session.scalar(select(func.count()).select_from(ActivityEvent).where(ActivityEvent.path_snapshot["resource_id"].astext == rid))
    history = resource_reference_count(session, row.id)
    return {"shared_resources": shared or 0, "activity_kits": kits or 0, "owned_uploads": uploads or 0,
            "activity_records": activity or 0, "conversation_references": history or 0}


@router.get("/{resource_id}/delete-preview")
def deletion_preview(request: Request, _: Admin, resource_id: UUID):
    with db(request).session() as session:
        row = session.get(Resource, resource_id)
        if row is None or row.deleted_at is not None: fail(404, "resource_not_found")
        return {"resource": admin_data(session, row), "dependencies": deletion_dependencies(session, row),
                "recoverable_in_admin": False, "media_retained": True}


def delete_resource_in_session(session, principal, resource_id, body):
    if body.confirm_resource_id != resource_id: fail(422, "resource_delete_confirmation_required")
    row = session.scalar(select(Resource).where(Resource.id == resource_id).with_for_update())
    if row is None: fail(404, "resource_not_found")
    if row.deleted_at is not None:
        # A lost-response retry confirms this administrator's identical deletion.
        if row.deleted_by == principal["id"] and row.version == body.expected_version + 1:
            return {"status": "deleted", "id": str(row.id), "version": row.version, "media_retained": True}
        fail(404, "resource_not_found")
    if row.version != body.expected_version: fail(409, "stale_version")
    dependencies = deletion_dependencies(session, row)
    row.deletion_snapshot = {"resource": admin_data(session, row), "dependencies": dependencies,
                             "retention": "Media and historical references retained; no storage purge."}
    session.execute(delete(ResourceTopic).where(ResourceTopic.resource_id == row.id))
    row.deleted_at = datetime.now(timezone.utc); row.deleted_by = principal["id"]
    row.published = False; row.version += 1
    session.flush()
    return {"status": "deleted", "id": str(row.id), "version": row.version, "media_retained": True}


@router.post("/{resource_id}/delete")
def delete_resource(request: Request, principal: Admin, resource_id: UUID, body: DeleteResource):
    with db(request).session() as session, session.begin():
        return delete_resource_in_session(session, principal, resource_id, body)
