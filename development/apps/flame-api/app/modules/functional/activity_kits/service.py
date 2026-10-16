"""Kit publication rules reused by administration and learner eligibility."""
from sqlalchemy import select
from app.modules.functional.activity_kits.models import KitTopic
from app.modules.functional.curriculum.public_paths import path_info
from app.core.domain_errors import fail
from app.modules.functional.resources.storage import ResourceStorage, StorageUnavailable


def publication_check(session, row, settings):
    if not row.name.strip() or not row.description or not row.materials or not row.instructions or not row.supervision:
        fail(422, "incomplete_kit")
    if not row.image_keys:
        fail(422, "kit_image_required")
    paths = session.scalars(select(KitTopic).where(KitTopic.kit_id == row.id)).all()
    if not paths:
        fail(422, "kit_path_required")
    for path in paths:
        path_info(session, path.topic_id, path.subtopic_id, published=True)
    storage = ResourceStorage(settings)
    try:
        if any(not storage.exists(key) for key in row.image_keys):
            fail(422, "kit_image_missing")
    except StorageUnavailable:
        fail(503, "resource_storage_unavailable")


