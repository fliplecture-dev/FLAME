"""Resource-owned static video posters; reuse private upload ownership and signing."""
from time import time
from sqlalchemy import select
from app.core.domain_errors import fail
from app.modules.functional.resources.models import ResourceUpload
from app.modules.functional.resources.storage import ResourceStorage, StorageUnavailable
from app.modules.functional.resources.service import local_signature
from app.modules.functional.resources.external_video import video_data


def assign_thumbnail(session, row, upload_id, auth_subject):
    if upload_id is None:
        row.thumbnail_storage_key = None
        return
    if row.type != "video": fail(422, "video_thumbnail_type_required")
    upload = session.scalar(select(ResourceUpload).where(ResourceUpload.id == upload_id).with_for_update())
    if upload is None or upload.owner_auth_subject != auth_subject: fail(404, "upload_not_found")
    if upload.kit_id is not None or upload.resource_id not in (None, row.id): fail(409, "upload_already_used")
    if upload.media_type != "image" or upload.mime_type not in {"image/png", "image/jpeg", "image/webp"}:
        fail(422, "video_thumbnail_image_required")
    row.thumbnail_storage_key = upload.storage_key
    upload.resource_id = row.id


def thumbnail_delivery(row, config, preview=False):
    key = row.thumbnail_storage_key
    if not key:
        url = (video_data(row) or {}).get("thumbnail_url")
        if url: return {"url": url, "version": row.version, "launch_mode": "media", "expires_at": None}
        fail(404, "video_thumbnail_missing")
    storage = ResourceStorage(config)
    try:
        if not storage.exists(key): fail(404, "resource_asset_missing")
        expires = int(time()) + 300
        if preview and config.resource_storage_backend == "local":
            url = f"/api/b9/admin/resources/{row.id}/preview-content?thumbnail=true"
        else:
            signature = ""
            if config.resource_storage_backend == "local":
                if not config.bff_shared_key: fail(503, "resource_delivery_unavailable")
                signature = local_signature(config.bff_shared_key.get_secret_value(), row.id, key, expires)
            url = storage.signed_url(row.id, key, expires, signature, thumbnail=True)
        return {"url": url, "version": row.version, "launch_mode": "media", "expires_at": expires}
    except StorageUnavailable:
        fail(503, "resource_delivery_unavailable")
