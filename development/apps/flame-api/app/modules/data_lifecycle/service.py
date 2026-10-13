"""Supabase Auth deletion and retry of confirmed, locally revoked accounts."""
from datetime import datetime, timezone
from uuid import UUID
import httpx
from sqlalchemy import select
from app.core.config import Settings
from app.modules.data_lifecycle.models import DeletionRequest
from app.modules.identity.models import StudentProfile

def delete_provider_user(settings: Settings, auth_subject: str) -> bool:
    """Hard-delete the exact owned Supabase user; 404 means an earlier attempt succeeded."""
    if not settings.supabase_url or not (settings.supabase_secret_key or settings.supabase_service_role_key):
        return False
    try:
        user_id = UUID(auth_subject)
        if settings.supabase_secret_key:
            secret = settings.supabase_secret_key.get_secret_value()
            headers = {"apikey": secret}
        else:
            secret = settings.supabase_service_role_key.get_secret_value()
            headers = {"apikey": secret, "Authorization": "Bearer " + secret}
        response = httpx.delete(
            settings.supabase_url + "/auth/v1/admin/users/" + str(user_id),
            headers=headers,
            timeout=10,
        )
        return response.status_code in (200, 204, 404)
    except (ValueError, httpx.HTTPError):
        return False

def complete_provider_deletion(database, settings: Settings, receipt_id: UUID) -> bool:
    """Safe to retry after timeout or worker crash; never logs identity or credentials."""
    with database.session() as db:
        receipt = db.get(DeletionRequest, receipt_id)
        if receipt is None:
            return False
        if receipt.status == "completed":
            return True
        if receipt.status != "pending_provider":
            return False
        profile = db.get(StudentProfile, receipt.student_id)
        if profile is None or profile.status != "deleting":
            return False
        auth_subject = profile.auth_subject
    if not delete_provider_user(settings, auth_subject):
        return False
    with database.session() as db, db.begin():
        receipt = db.scalar(select(DeletionRequest).where(
            DeletionRequest.id == receipt_id).with_for_update())
        if receipt is None:
            return False
        if receipt.status == "completed":
            return True
        profile = db.scalar(select(StudentProfile).where(
            StudentProfile.id == receipt.student_id).with_for_update())
        if profile is None or profile.status != "deleting":
            return False
        profile.status = "deleted"
        receipt.status = "completed"
        receipt.completed_at = datetime.now(timezone.utc)
    return True

def purge_completed_tombstones(database, *, now=None, limit=100, retention_days=30) -> int:
    """Purge minimal local deletion receipts/tombstones after the policy window."""
    from datetime import timedelta
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=retention_days)
    with database.session() as db:
        ids = db.scalars(select(DeletionRequest.id).where(
            DeletionRequest.status == "completed",
            DeletionRequest.completed_at < cutoff).order_by(
            DeletionRequest.completed_at, DeletionRequest.id).limit(limit)).all()
    removed = 0
    for receipt_id in ids:
        with database.session() as db, db.begin():
            receipt = db.scalar(select(DeletionRequest).where(
                DeletionRequest.id == receipt_id).with_for_update())
            if receipt is None or receipt.status != "completed" or not receipt.completed_at or receipt.completed_at >= cutoff:
                continue
            profile = db.scalar(select(StudentProfile).where(
                StudentProfile.id == receipt.student_id).with_for_update())
            if profile is None or profile.status != "deleted":
                continue
            db.delete(receipt)
            db.flush()
            db.delete(profile)
            removed += 1
    return removed

