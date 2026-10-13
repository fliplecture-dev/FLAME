"""Reusable access guards for future member, admin, and owned-object routes."""
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request

from app.modules.identity.router import _principal, require_bff


def require_member(
    request: Request,
    _: Annotated[None, Depends(require_bff)],
    x_flame_session: Annotated[str | None, Header()] = None,
) -> dict:
    return _principal(request, x_flame_session)


def require_admin(principal: Annotated[dict, Depends(require_member)]) -> dict:
    if principal["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return principal


def require_owner(principal: dict, student_id: UUID) -> None:
    if principal["id"] != str(student_id):
        raise HTTPException(404, "Not found")
