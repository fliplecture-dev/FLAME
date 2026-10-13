"""Kit-owned eligibility and student-safe guide data; never execute an activity."""
from app.contracts.learning_metadata import candidate_metadata
from fastapi import HTTPException
from sqlalchemy import select, or_
from app.contracts.catalogue import CatalogueCandidate, availability
from app.modules.activity_kits.models import ActivityKit, KitTopic
from app.modules.activity_kits.service import publication_check
from app.modules.resources.storage import StorageUnavailable


def kit_card(row):
    return {"id": str(row.id), "version": row.version, "name": row.name, "description": row.description,
        "materials": row.materials, "instructions": row.instructions, "supervision": row.supervision,
        "cost": str(row.cost) if row.cost is not None else None, "currency": row.currency,
        "availability": row.availability, "prerequisites": "Review materials and supervision with a parent before starting."}


def eligible_candidates(db, topic_id, subtopic_id, config):
    rows = db.scalars(select(ActivityKit).join(KitTopic).where(ActivityKit.published.is_(True), KitTopic.topic_id == topic_id,
        or_(KitTopic.subtopic_id.is_(None), KitTopic.subtopic_id == subtopic_id) if subtopic_id else KitTopic.subtopic_id.is_(None)).distinct()).all()
    result = []
    precise = {link.kit_id for link in db.scalars(select(KitTopic).where(
        KitTopic.topic_id == topic_id, KitTopic.subtopic_id == subtopic_id))} if subtopic_id else set()
    for r in rows:
        if availability(r.availability) != "available":
            continue
        try:
            publication_check(db, r, config)
        except (HTTPException, StorageUnavailable):
            continue
        result.append(CatalogueCandidate(**candidate_metadata(r.learning_metadata), id=r.id, kind="kit", type="activity_kit", version=r.version,
            title=r.name, description=r.description, metadata=" ".join([*r.materials, r.instructions or "", r.supervision or ""]),
            availability_state=availability(r.availability), precise_mapping=r.id in precise, card=kit_card(r)))
    return result
