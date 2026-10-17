"""Member-owned profile editing. Contact/address data never enters AI prompts."""
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from app.modules.functional.identity.dependencies import require_member
from app.modules.functional.identity.models import StudentProfile
from app.modules.functional.identity.profile_data import ProfileEdit

router = APIRouter(prefix="/api/v1/me")
Member = Annotated[dict, Depends(require_member)]
FIELDS = tuple(ProfileEdit.model_fields)


def owned_profile(db, principal, *, lock=False):
    query = select(StudentProfile).where(StudentProfile.id == UUID(principal["id"]))
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None or row.status != "active":
        raise HTTPException(403, "account_inactive")
    return row


def project(row):
    return {"email": row.email, **{field: getattr(row, field) for field in FIELDS}}


@router.get("/profile")
def read_profile(request: Request, principal: Member):
    with request.app.state.database.session() as db:
        return project(owned_profile(db, principal))


@router.patch("/profile")
def edit_profile(request: Request, body: ProfileEdit, principal: Member):
    with request.app.state.database.session() as db, db.begin():
        row = owned_profile(db, principal, lock=True)
        for name, value in body.model_dump(exclude_unset=True).items():
            setattr(row, name, value)
        db.flush()
        return project(row)
