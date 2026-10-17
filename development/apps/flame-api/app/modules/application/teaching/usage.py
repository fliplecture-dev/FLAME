"""Fixed guest/member calendar-day limits; no membership-tier policy engine."""
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import func, select
from app.modules.functional.conversations.models import AnswerRequest

INDIA_TIME = timezone(timedelta(hours=5, minutes=30), "Asia/Kolkata")


def quota_day_start(now=None):
    now = now or datetime.now(timezone.utc)
    return now.astimezone(INDIA_TIME).replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def daily_usage_limit(principal: dict, member_limit: int) -> int | None:
    if principal.get("role") == "admin":
        return None
    return min(10 if principal.get("role") == "guest" else 25, member_limit)


def usage_status(database, principal, ceiling):
    start = quota_day_start()
    with database.session() as db:
        used = db.scalar(select(func.count()).select_from(AnswerRequest).where(
            AnswerRequest.student_id == UUID(principal["id"]), AnswerRequest.created_at >= start, AnswerRequest.created_at < start + timedelta(days=1))) or 0
    limit = daily_usage_limit(principal, ceiling)
    return {"limit": limit, "used": used, "remaining": max(0, limit-used) if limit is not None else None,
            "resets_at": (start+timedelta(days=1)).isoformat(), "timezone": "Asia/Kolkata"}
