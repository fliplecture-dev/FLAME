"""Server-issued guest capability scoped to one anonymous browser identity."""
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated
from uuid import uuid4
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from app.modules.functional.identity.models import GuestAccess, StudentProfile
from app.modules.functional.identity.router import require_bff

router = APIRouter(prefix="/api/v1/guest")


def require_guest(request: Request, _: Annotated[None, Depends(require_bff)],
                  x_flame_guest: Annotated[str | None, Header()] = None):
    if not x_flame_guest or not 32 <= len(x_flame_guest) <= 200:
        raise HTTPException(401, "guest_access_required")
    with request.app.state.database.session() as db:
        access = db.get(GuestAccess, sha256(x_flame_guest.encode()).hexdigest())
        if access is None:
            raise HTTPException(401, "guest_access_expired")
        expires = access.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires <= datetime.now(timezone.utc):
            raise HTTPException(401, "guest_access_expired")
        profile = db.get(StudentProfile, access.student_id)
        if profile is None or profile.status != "guest":
            raise HTTPException(403, "guest_access_unavailable")
        return {"id": str(profile.id), "role": "guest"}


@router.post("/identity", dependencies=[Depends(require_bff)], status_code=201)
def create_identity(request: Request):
    raw = token_urlsafe(48)
    with request.app.state.database.session() as db, db.begin():
        profile = StudentProfile(id=uuid4(), auth_subject="guest:" + str(uuid4()), status="guest")
        db.add(profile); db.flush()
        db.add(GuestAccess(id_hash=sha256(raw.encode()).hexdigest(), student_id=profile.id,
                           expires_at=datetime.now(timezone.utc) + timedelta(days=7)))
    return {"token": raw}


@router.get("/me")
def guest_me(principal: Annotated[dict, Depends(require_guest)]):
    return {"role": "guest"}
