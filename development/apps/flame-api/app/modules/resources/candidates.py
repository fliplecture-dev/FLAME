"""Media-owned candidate eligibility; no recommendation ranking or persistence."""
from app.contracts.learning_metadata import candidate_metadata
from fastapi import HTTPException
from sqlalchemy import or_, select
from app.contracts.catalogue import CatalogueCandidate
from app.modules.resources.models import Resource, ResourceTopic
from app.modules.resources.external_video import parse_video, is_provider_url, learner_video_policy
from app.modules.resources.service import public_data
from app.modules.resources.storage import ResourceStorage, StorageUnavailable
from app.modules.resources.validation import validate_external_url, MediaRejected


def playable(row, config, asset_checks=None):
    try:
        if row.type in {"video", "external_video"} and is_provider_url(row.external_url):
            parse_video(row.external_url)
        elif row.external_url:
            if is_provider_url(row.external_url):
                return False
            validate_external_url(row.external_url, {h.strip().lower() for h in config.resource_allowed_hosts.split(",") if h.strip()})
        elif not row.storage_key:
            return False
        else:
            key = (config.resource_storage_backend, config.resource_local_dir,
                   config.supabase_url, config.resource_storage_bucket, row.storage_key)
            # A curiosity browse can match the same media through multiple paths.
            # Reuse checks only within this request's database session; the next
            # request must observe removed objects and changed storage settings.
            if asset_checks is not None and key in asset_checks:
                exists = asset_checks[key]
            else:
                exists = ResourceStorage(config).exists(row.storage_key)
                if asset_checks is not None:
                    asset_checks[key] = exists
            if not exists:
                return False
        return True
    except (HTTPException, MediaRejected, StorageUnavailable):
        return False


def eligible_candidates(db, topic_id, subtopic_id, config):
    asset_checks = db.info.setdefault("resource_asset_checks", {})
    rows = db.scalars(select(Resource).join(ResourceTopic).where(
        Resource.type.in_(["image", "video", "interactive"]), Resource.deleted_at.is_(None), Resource.published.is_(True), Resource.availability == "available",
        *learner_video_policy(Resource), ResourceTopic.topic_id == topic_id,
        or_(ResourceTopic.subtopic_id.is_(None), ResourceTopic.subtopic_id == subtopic_id)
        if subtopic_id else ResourceTopic.subtopic_id.is_(None)).distinct()).all()
    precise = {link.resource_id for link in db.scalars(select(ResourceTopic).where(
        ResourceTopic.topic_id == topic_id, ResourceTopic.subtopic_id == subtopic_id))} if subtopic_id else set()
    return [CatalogueCandidate(**candidate_metadata(r.learning_metadata), id=r.id, kind="resource", type=r.type, version=r.version, title=r.title,
        description=r.description, metadata=" ".join(filter(None, [r.alt_text, r.caption_or_transcript, r.accessibility_note])),
        availability_state="available", precise_mapping=r.id in precise, card=public_data(r), mime_type=r.mime_type,
        alt_text=r.alt_text, caption_or_transcript=r.caption_or_transcript, accessibility_note=r.accessibility_note)
        for r in rows if playable(r, config, asset_checks)]
