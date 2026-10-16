"""B9 resource publication, path eligibility and member cards."""
from app.contracts.learning_metadata import metadata_data
import hashlib
import hmac
from time import time
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.modules.functional.curriculum.catalogue import ancestor_curriculum, nodes
from app.modules.functional.curriculum.models import Curriculum, Category, Domain, Level, Subject, Topic, Subtopic
from app.modules.functional.resources.models import Resource, ResourceTopic, ResourceUpload
from app.modules.functional.resources.storage import ResourceStorage, StorageUnavailable
from app.modules.functional.resources.validation import MediaRejected, validate_external_url
from app.modules.functional.resources.external_video import inspect_video, video_data, is_provider_url, reject as video_reject


# Historical imports stay valid; curriculum owns path validation.
from app.core.domain_errors import fail
from app.modules.functional.curriculum.public_paths import path_info


def path_choices(session, curriculum_id):
    curriculum = session.get(Curriculum, curriculum_id)
    if curriculum is None or curriculum.state == "archived":
        fail(404, "curriculum_not_found")
    groups = nodes(session, curriculum_id)
    levels, subjects, domains, categories, topics, subtopics = [{n.id: n for n in group} for group in groups]
    result = []
    for topic in topics.values():
        domain = domains.get(topic.domain_id)
        subject = subjects.get(domain.subject_id) if domain else None
        level = levels.get(subject.level_id) if subject else None
        category = categories.get(topic.category_id)
        if not level or (topic.category_id and not category):
            continue
        names = {"level": level.name, "subject": subject.name, "domain": domain.name,
                 "category": category.name if category else "", "topic": topic.name}
        label = " / ".join([curriculum.name, *[name for name in names.values() if name]])
        common = {"topic_id": str(topic.id), "subject_id": str(subject.id), "curriculum_id": str(curriculum.id),
                  "curriculum": curriculum.name, "level_id": str(level.id), "domain_id": str(domain.id),
                  "category_id": str(category.id) if category else None,
                  **names, "available_for_publication": curriculum.state == "published"}
        result.append({**common, "subtopic_id": None, "subtopic": "", "label": label})
        for leaf in subtopics.values():
            if leaf.topic_id == topic.id:
                result.append({**common, "subtopic_id": str(leaf.id), "subtopic": leaf.name,
                               "label": label + " / " + leaf.name})
    return sorted(result, key=lambda item: item["label"].casefold())


def resource_path_context(session, paths, *, lock=False):
    topic_ids = {path.topic_id for path in paths}
    leaf_ids = {path.subtopic_id for path in paths if path.subtopic_id}
    query = (select(Topic, Domain, Subject, Level, Curriculum, Category)
             .join(Domain, Topic.domain_id == Domain.id)
             .join(Subject, Domain.subject_id == Subject.id)
             .join(Level, Subject.level_id == Level.id)
             .join(Curriculum, Level.curriculum_id == Curriculum.id)
             .outerjoin(Category, Topic.category_id == Category.id)
             .where(Topic.id.in_(topic_ids)))
    if lock:
        query = query.order_by(Curriculum.id, Topic.id).with_for_update(of=Curriculum)
    contexts = {row[0].id: row for row in session.execute(query).all()} if topic_ids else {}
    leaves = {leaf.id: leaf for leaf in session.scalars(select(Subtopic).where(Subtopic.id.in_(leaf_ids)))} if leaf_ids else {}
    return contexts, leaves


def valid_resource_link(context, leaf, subtopic_id):
    if not context:
        return False
    topic, domain, subject, level, curriculum, category = context
    return (curriculum.state != "archived" and not any(node.archived for node in (topic, domain, subject, level))
            and (not topic.category_id or category is not None and not category.archived)
            and (not subtopic_id or leaf is not None and not leaf.archived and leaf.topic_id == topic.id))


def validate_resource_paths(session, paths):
    contexts, leaves = resource_path_context(session, paths, lock=True)
    invalid = [{"topic_id": str(path.topic_id), "subtopic_id": str(path.subtopic_id) if path.subtopic_id else None}
               for path in paths if not valid_resource_link(contexts.get(path.topic_id), leaves.get(path.subtopic_id), path.subtopic_id)]
    if invalid:
        raise HTTPException(422, {"code": "resource_paths_unavailable", "field": "paths", "invalid_paths": invalid})


def active_associations(session, resource: Resource):
    associations = session.scalars(select(ResourceTopic).where(ResourceTopic.resource_id == resource.id)).all()
    contexts, leaves = resource_path_context(session, associations)
    active = []
    for path in associations:
        context = contexts.get(path.topic_id)
        if valid_resource_link(context, leaves.get(path.subtopic_id), path.subtopic_id) and context[4].state == "published":
            topic, domain, subject, level, curriculum, category = context
            active.append({"curriculum_id": curriculum.id, "curriculum_revision": curriculum.revision,
                           "level_id": level.id, "subject_id": subject.id, "topic_id": topic.id, "subtopic_id": path.subtopic_id})
    return active


def publication_check(session, resource: Resource, settings):
    if resource.type=="interactive" and not resource.storage_key and not resource.external_url: fail(422, "interactive_media_required")
    if resource.type != "video" and is_provider_url(resource.external_url): video_reject("external_video_type_required")
    if resource.availability != "available":
        fail(422, "resource_unavailable")
    missing_rights = [field for field in ("rights_basis", "rights_holder", "distribution_scope")
                      if not (getattr(resource, field) or "").strip()]
    if missing_rights:
        raise HTTPException(422, {"code": "distribution_rights_required", "fields": missing_rights})
    if resource.rights_basis in {"licensed", "permission"} and not (resource.rights_reference or "").strip():
        fail(422, "rights_reference_required")
    if resource.type == "interactive" and resource.mime_type == "text/html" and not (resource.accessibility_note or "").strip():
        fail(422, "interactive_accessibility_required")
    if resource.type == "video" and resource.storage_key and resource.mime_type in {"video/mp4", "video/webm"} and not resource.thumbnail_storage_key:
        fail(422, "video_thumbnail_required")
    if resource.thumbnail_storage_key:
        try:
            if not ResourceStorage(settings).exists(resource.thumbnail_storage_key): fail(422, "resource_asset_missing")
        except StorageUnavailable: fail(503, "resource_storage_unavailable")
    is_gif = resource.type == "video" and resource.mime_type == "image/gif"
    if (resource.type in {"image", "diagram"} or is_gif) and (not (resource.alt_text or "").strip() or is_gif and (resource.alt_text or "").strip().casefold() in {"gif", "png", "jpg", "jpeg", "webp", "image", "animation", "picture", "file", "diagram", "photo"}):
        fail(422, "alt_text_required")
    if resource.type in {"audio", "video", "animation", "external_video"} and not is_gif and not (resource.caption_or_transcript or resource.accessibility_note):
        fail(422, "accessibility_note_required")
    if resource.type == "video" and is_provider_url(resource.external_url):
        info = inspect_video(resource.external_url, settings)
        resource.external_video = info
    elif resource.storage_key:
        try:
            if not ResourceStorage(settings).exists(resource.storage_key):
                fail(422, "resource_asset_missing")
        except StorageUnavailable:
            fail(503, "resource_storage_unavailable")
    elif resource.external_url:
        allowed = {host.strip().lower() for host in settings.resource_allowed_hosts.split(",") if host.strip()}
        try:
            validate_external_url(resource.external_url, allowed)
        except MediaRejected as exc:
            fail(422, str(exc))
    else:
        fail(422, "resource_source_required")


def admin_data(session, resource: Resource):
    paths = session.scalars(select(ResourceTopic).where(ResourceTopic.resource_id == resource.id)).all()
    upload_id = session.scalar(select(ResourceUpload.id).where(ResourceUpload.resource_id == resource.id,
                                                               ResourceUpload.storage_key == resource.storage_key)) if resource.storage_key else None
    upload = session.get(ResourceUpload, upload_id) if upload_id else None
    contexts, leaves = resource_path_context(session, paths)
    details = []
    for association in paths:
        context = contexts.get(association.topic_id)
        leaf = leaves.get(association.subtopic_id)
        valid = valid_resource_link(context, leaf, association.subtopic_id)
        if context:
            topic, domain, subject, level, curriculum, category = context
            names = {"level": level.name, "subject": subject.name, "domain": domain.name,
                     "category": category.name if category else "", "topic": topic.name, "subtopic": leaf.name if leaf else ""}
            details.append({"topic_id": str(topic.id), "subtopic_id": str(association.subtopic_id) if association.subtopic_id else None,
                            "subject_id": str(subject.id), "curriculum_id": str(curriculum.id),
                  "curriculum": curriculum.name, "level_id": str(level.id), "domain_id": str(domain.id),
                  "category_id": str(category.id) if category else None, **names,
                            "label": " / ".join([curriculum.name, *[n for n in names.values() if n]]), "valid": valid,
                            "available_for_publication": valid and curriculum.state == "published"})
        else:
            details.append({"topic_id": str(association.topic_id), "subtopic_id": str(association.subtopic_id) if association.subtopic_id else None,
                            "label": "Unavailable curriculum path", "valid": False})
    return {"learning_metadata": metadata_data(resource.learning_metadata), "id": str(resource.id), "type": resource.type, "title": resource.title,
            "upload_id": str(upload_id) if upload_id else None,
            "has_thumbnail": bool(resource.thumbnail_storage_key),
            "thumbnail_upload_id": str(session.scalar(select(ResourceUpload.id).where(ResourceUpload.storage_key == resource.thumbnail_storage_key))) if resource.thumbnail_storage_key else None,
            "description": resource.description, "version": resource.version, "published": resource.published,
            "availability": resource.availability, "media_ready":bool(resource.storage_key or resource.external_url), "source": "upload" if resource.storage_key else "external" if resource.external_url else "pending",
            "external_url": resource.external_url, "mime_type": resource.mime_type,
            "external_video": video_data(resource),
            "byte_size": resource.byte_size, "file_name": upload.file_name if upload else None,
            "updated_at": resource.updated_at.isoformat(), "created_at": resource.created_at.isoformat(), "alt_text": resource.alt_text,
            "caption_or_transcript": resource.caption_or_transcript,
            "accessibility_note": resource.accessibility_note,
            "rights_basis": resource.rights_basis, "rights_holder": resource.rights_holder,
            "rights_reference": resource.rights_reference, "attribution": resource.attribution,
            "distribution_scope": resource.distribution_scope,
            "path_details": details,
            "paths": [{"topic_id": str(p.topic_id),
                       "subtopic_id": str(p.subtopic_id) if p.subtopic_id else None} for p in paths]}


def public_data(resource: Resource):
    return {"id": str(resource.id), "type": resource.type, "title": resource.title,
            "description": resource.description, "version": resource.version, "mime_type": resource.mime_type,
            "alt_text": resource.alt_text, "caption_or_transcript": resource.caption_or_transcript,
            "accessibility_note": resource.accessibility_note, "attribution": resource.attribution,
            "has_thumbnail": bool(resource.thumbnail_storage_key),
            "thumbnail_url": (video_data(resource) or {}).get("thumbnail_url"),
            "availability": resource.availability, "delivery_url": f"/api/v1/resources/{resource.id}/delivery"}


def local_signature(secret: str, resource_id: UUID, key: str, expires: int) -> str:
    payload = f"{resource_id}:{key}:{expires}".encode()
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_local_signature(secret: str, resource_id: UUID, key: str, expires: int, signature: str) -> bool:
    return int(time()) <= expires <= int(time()) + 300 and hmac.compare_digest(
        local_signature(secret, resource_id, key, expires), signature)

