"""Compatibility URLs over recommendation services; no catalogue or persistence rules here."""
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from app.modules.identity.dependencies import require_member
from app.modules.recommendations import service
from app.modules.learning_response.composer import compose_recommendations

router = APIRouter(prefix="/api/v1/sessions", tags=["recommendations"])
Member = Annotated[dict, Depends(require_member)]


class ImageDisplayed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID
    resource_id: UUID
    resource_version: int = Field(ge=1)
    display_status: Literal["displayed", "failed"] = "displayed"


class RecommendationDisplayed(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID
    candidate_id: UUID
    version: int = Field(ge=1)


@router.get("/{session_id}/recommendations")
def recommendations(request: Request, principal: Member, session_id: UUID, message_id: UUID):
    def load():
        with request.app.state.database.session() as db, db.begin():
            return service.recommend(db, request.app.state.settings, UUID(principal["id"]), session_id, message_id)
    # Catch failures after transaction rollback, never commit half a selection.
    return compose_recommendations(message_id, load)


@router.post("/{session_id}/images/displayed")
def image_displayed(request: Request, principal: Member, session_id: UUID, body: ImageDisplayed):
    with request.app.state.database.session() as db, db.begin():
        return service.mark_image(db, request.app.state.settings, UUID(principal["id"]), session_id, body)


@router.post("/{session_id}/recommendations/displayed")
def recommendation_displayed(request: Request, principal: Member, session_id: UUID, body: RecommendationDisplayed):
    with request.app.state.database.session() as db, db.begin():
        return service.mark_card(db, request.app.state.settings, UUID(principal["id"]), session_id, body)


@router.get("/{session_id}/recommendations/{candidate_id}")
def open_candidate(request: Request, principal: Member, session_id: UUID, candidate_id: UUID, message_id: UUID):
    with request.app.state.database.session() as db, db.begin():
        return service.open_candidate(db, request.app.state.settings, UUID(principal["id"]), session_id, candidate_id, message_id)
