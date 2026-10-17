"""Guest Curiosity transport reuses the owned, quota-safe answer pipeline."""
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from app.modules.functional.identity.dependencies import require_member
from app.modules.functional.identity.guests import require_guest
from app.modules.functional.identity.models import StudentProfile
from app.modules.functional.conversations.models import ConversationSession
from app.modules.functional.conversations.router import owned, session_data
from app.modules.application.teaching.answer_router import ask_question, ask_stream, check_capability, CapabilityCheck
from app.modules.application.teaching.schemas import AnswerRequest
from app.modules.application.teaching.simulation_router import simulation, SimulationRequest
from app.modules.application.teaching.usage import usage_status

router = APIRouter(prefix="/api/v1")
Guest = Annotated[dict, Depends(require_guest)]


class GuestSessionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["curiosity"] = "curiosity"
    context: None = None


class GuestAnswer(AnswerRequest):
    mode: Literal["curiosity"] = "curiosity"
    context: None = None


def guest_conversation(request, principal, session_id):
    with request.app.state.database.session() as db:
        row = owned(db, UUID(principal["id"]), session_id)
        if row.mode != "curiosity":
            raise HTTPException(403, "Sign in to use Study mode")


@router.post("/guest/sessions", status_code=201)
def create_guest_conversation(request: Request, body: GuestSessionInput, principal: Guest):
    with request.app.state.database.session() as db, db.begin():
        profile = db.scalar(select(StudentProfile).where(StudentProfile.id == UUID(principal["id"])).with_for_update())
        if profile is None or profile.status != "guest":
            raise HTTPException(403, "Guest access unavailable")
        # One anonymous conversation per browser identity prevents session churn.
        row = db.scalar(select(ConversationSession).where(ConversationSession.student_id == profile.id,
                        ConversationSession.mode == "curiosity").order_by(ConversationSession.created_at).limit(1))
        if row is None:
            now = datetime.now(timezone.utc)
            row = ConversationSession(student_id=profile.id, mode="curiosity", created_at=now, updated_at=now, recent_at=now)
            db.add(row); db.flush()
        return session_data(row)


@router.post("/guest/sessions/{session_id}/capability-check")
def guest_capability(request: Request, session_id: UUID, body: CapabilityCheck, principal: Guest):
    guest_conversation(request, principal, session_id)
    return check_capability(request, session_id, body, principal)


@router.post("/guest/sessions/{session_id}/ask")
def guest_ask(request: Request, session_id: UUID, body: GuestAnswer, principal: Guest,
              idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]):
    guest_conversation(request, principal, session_id)
    return ask_question(request, session_id, body, principal, idempotency_key)


@router.post("/guest/sessions/{session_id}/ask-stream")
def guest_stream(request: Request, session_id: UUID, body: GuestAnswer, principal: Guest,
                 idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]):
    guest_conversation(request, principal, session_id)
    return ask_stream(request, session_id, body, principal, idempotency_key)


@router.post("/guest/sessions/{session_id}/simulation")
def guest_simulation(request: Request, session_id: UUID, body: SimulationRequest, principal: Guest):
    guest_conversation(request, principal, session_id)
    return simulation(request, session_id, body, principal)


@router.get("/guest/usage")
def guest_usage(request: Request, principal: Guest):
    return usage_status(request.app.state.database, principal, request.app.state.settings.llm_daily_request_limit)


@router.get("/me/usage")
def member_usage(request: Request, principal: Annotated[dict, Depends(require_member)]):
    return usage_status(request.app.state.database, principal, request.app.state.settings.llm_daily_request_limit)
