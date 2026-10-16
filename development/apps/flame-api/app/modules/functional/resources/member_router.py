"""Published member resource lookup, delivery and measured open/play events."""
from datetime import datetime, timezone
from pathlib import Path
from time import time
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import and_, or_, select

from app.modules.functional.conversations.models import ConversationSession
from app.modules.functional.identity.dependencies import require_member
from app.modules.functional.identity.models import StudentProfile
from app.modules.functional.resources.models import Resource, ResourceTopic
from app.modules.functional.resources.service import fail, local_signature, path_info, public_data, verify_local_signature
from app.modules.functional.resources.storage import ResourceStorage, StorageUnavailable
from app.modules.functional.resources.validation import MediaRejected, validate_external_url
from app.modules.functional.resources.external_video import is_provider_url, learner_video_policy, embed_url, video_data
from app.modules.functional.student_activity.models import ActivityEvent

router = APIRouter(prefix="/api/v1/resources", tags=["resources"])
Member = Annotated[dict, Depends(require_member)]


def db(request):
    return request.app.state.database


def current_resource(session, resource_id: UUID):
    row = session.get(Resource, resource_id)
    if row is None or row.deleted_at is not None or not row.published or row.availability != "available":
        fail(404, "resource_not_found")
    associations = session.scalars(select(ResourceTopic).where(ResourceTopic.resource_id == row.id)).all()
    if not associations:
        fail(404, "resource_not_found")
    for association in associations:
        try:
            path_info(session, association.topic_id, association.subtopic_id, published=True)
            return row
        except HTTPException:
            continue
    fail(404, "resource_not_found")


@router.get("")
def lookup_resources(request: Request, _: Member, topic_id: UUID,
                     subtopic_id: UUID | None = None, type: str | None = None,
                     curriculum_revision: int | None = Query(None, ge=1),
                     offset: int = Query(0, ge=0), limit: int = Query(30, ge=1, le=100)):
    with db(request).session() as session:
        path = path_info(session, topic_id, subtopic_id, published=True)
        if curriculum_revision is not None and curriculum_revision != path["curriculum_revision"]:
            fail(409, "curriculum_revision_changed")
        query = select(Resource).join(ResourceTopic, ResourceTopic.resource_id == Resource.id).where(
            Resource.type.in_(["image", "video", "interactive"]), Resource.deleted_at.is_(None), Resource.published.is_(True), Resource.availability == "available", *learner_video_policy(Resource),
            ResourceTopic.topic_id == topic_id)
        if subtopic_id:
            query = query.where(or_(ResourceTopic.subtopic_id.is_(None),
                                    ResourceTopic.subtopic_id == subtopic_id))
        else:
            query = query.where(ResourceTopic.subtopic_id.is_(None))
        if type:
            query = query.where(Resource.type == type)
        rows = session.scalars(query.distinct().order_by(Resource.title, Resource.id)
                               .offset(offset).limit(limit)).all()
        return {"status": "ok" if rows else "no_results", "route": "resource_lookup",
                "knowledge_source": "resource_catalog", "grounded": False,
                "confidence": None, "blocks": [], "citations": [], "model_usage": None, "curriculum_version": f"revision-{path['curriculum_revision']}",
                "items": [public_data(row) for row in rows], "offset": offset, "limit": limit}


@router.get("/{resource_id}/delivery")
def resource_delivery(request: Request, _: Member, resource_id: UUID, topic_id: UUID | None = None,
                      subtopic_id: UUID | None = None, curriculum_revision: int | None = Query(None, ge=1),
                      version: int | None = Query(None, ge=1), language: str | None = Query(None, max_length=35), thumbnail: bool = False):
    config = request.app.state.settings
    with db(request).session() as session:
        if topic_id is not None:
            from app.modules.functional.curriculum.public_paths import describe_browse_path
            from app.modules.functional.resources.candidates import eligible_candidates
            from app.contracts.catalogue import suitable_for
            path = describe_browse_path(session, topic_id, subtopic_id)
            if curriculum_revision is not None and path["curriculum_revision"] != curriculum_revision:
                fail(409, "curriculum_revision_changed")
            if version is None:
                fail(422, "explore_version_changed")
            selected = next((item for item in eligible_candidates(session, topic_id, subtopic_id, config)
                             if item.id == resource_id and suitable_for(item, path["grade"], language)), None)
            if selected is None:
                fail(404, "explore_item_unavailable")
            if selected.version != version:
                fail(409, "explore_version_changed")
        row = current_resource(session, resource_id)
        if thumbnail:
            from app.modules.functional.resources.thumbnails import thumbnail_delivery
            return thumbnail_delivery(row, config)
        if row.type == "interactive" and row.mime_type == "text/html":
            from app.modules.functional.resources.interactive import interactive_data
            return {"status": "ok", **interactive_data(row, ResourceStorage(config))}
        if row.type in {"video", "external_video"} and is_provider_url(row.external_url):
            return {"status": "ok", "version": row.version, "launch_mode": "external_video", "url": embed_url(row), "external_video": video_data(row), "expires_at": None}
        if is_provider_url(row.external_url): fail(422, "external_video_type_required")
        if row.external_url:
            allowed = {host.strip().lower() for host in config.resource_allowed_hosts.split(",") if host.strip()}
            try:
                url = validate_external_url(row.external_url, allowed)
            except MediaRejected:
                fail(404, "resource_unavailable")
            return {"status": "ok", "url": url, "expires_at": None, "version": row.version,
                    "launch_mode": "separate_page" if row.type == "interactive" else "media"}
        if not row.storage_key:
            fail(404, "resource_unavailable")
        storage = ResourceStorage(config)
        try:
            if not storage.exists(row.storage_key):
                fail(404, "resource_asset_missing")
            expires = int(time()) + 300
            if config.resource_storage_backend == "local":
                secret = config.bff_shared_key
                if not secret:
                    fail(503, "resource_delivery_unavailable")
                signature = local_signature(secret.get_secret_value(), row.id, row.storage_key, expires)
            else:
                signature = ""
            url = storage.signed_url(row.id, row.storage_key, expires, signature)
        except StorageUnavailable:
            fail(503, "resource_delivery_unavailable")
        poster = None
        if row.thumbnail_storage_key:
            from app.modules.functional.resources.thumbnails import thumbnail_delivery
            poster = thumbnail_delivery(row, config)["url"]
        return {"status": "ok", "poster_url": poster, "url": url, "version": row.version,
                "expires_at": datetime.fromtimestamp(expires, timezone.utc).isoformat(),
                "launch_mode": "media"}


@router.get("/{resource_id}/content")
def local_resource_content(request: Request, resource_id: UUID, expires: int, signature: str, thumbnail: bool = False):
    config = request.app.state.settings
    if config.resource_storage_backend != "local" or not config.bff_shared_key:
        fail(404, "resource_not_found")
    with db(request).session() as session:
        row = current_resource(session, resource_id)
        if row.type == "interactive" or row.mime_type == "text/html":
            fail(404, "resource_not_found")
        asset_key = row.thumbnail_storage_key if thumbnail else row.storage_key
        if not asset_key or not verify_local_signature(
            config.bff_shared_key.get_secret_value(), resource_id, asset_key, expires, signature):
            fail(404, "resource_not_found")
        storage = ResourceStorage(config)
        try:
            key = storage.checked_key(asset_key)
        except StorageUnavailable:
            fail(404, "resource_not_found")
        target = storage.local_path(key)
        if not target.is_file():
            fail(404, "resource_asset_missing")
        return FileResponse(target, media_type=("image/" + ("jpeg" if key.endswith((".jpg", ".jpeg")) else key.rsplit(".", 1)[1])) if thumbnail else row.mime_type or "application/octet-stream",
                            headers={"X-Content-Type-Options": "nosniff",
                                     "Cache-Control": "private, no-store"})


class ResourceActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: str
    deduplication_key: str = Field(min_length=8, max_length=255)
    session_id: UUID | None = None


@router.post("/{resource_id}/activity")
def resource_activity(request: Request, principal: Member, resource_id: UUID, body: ResourceActivity):
    if body.event_type not in ("open", "play"):
        fail(422, "unsupported_activity")
    student_id = UUID(principal["id"])
    with db(request).session() as session, session.begin():
        session.scalar(select(StudentProfile).where(StudentProfile.id == student_id).with_for_update())
        row = current_resource(session, resource_id)
        if body.session_id:
            owned = session.get(ConversationSession, body.session_id)
            if owned is None or owned.student_id != student_id:
                fail(404, "session_not_found")
        existing = session.scalar(select(ActivityEvent).where(
            ActivityEvent.student_id == student_id, ActivityEvent.deduplication_key == body.deduplication_key))
        if existing:
            snapshot = existing.path_snapshot or {}
            if existing.event_type != "resource_" + body.event_type or snapshot.get("resource_id") != str(resource_id):
                fail(409, "idempotency_conflict")
            return {"status": "ok", "event_id": str(existing.id), "replayed": True}
        event = ActivityEvent(student_id=student_id, session_id=body.session_id,
                              event_type="resource_" + body.event_type,
                              path_snapshot={"resource_id": str(row.id), "resource_type": row.type},
                              deduplication_key=body.deduplication_key)
        session.add(event)
        session.flush()
        return {"status": "ok", "event_id": str(event.id), "replayed": False}
