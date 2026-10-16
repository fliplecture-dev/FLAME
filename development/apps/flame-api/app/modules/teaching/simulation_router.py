"""Owner-checked ephemeral source; saved text is independent of this extra provider call."""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.modules.conversations.models import Message
from app.modules.conversations.router import owned
from app.modules.identity.dependencies import require_member
from app.modules.teaching.simulations import generate, select_engine, transient
from app.modules.teaching.usage import daily_usage_limit

router = APIRouter(prefix="/api/v1")


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID
    start: bool = False


@router.post("/sessions/{session_id}/simulation")
def simulation(request: Request, session_id: UUID, body: SimulationRequest,
               principal: Annotated[dict, Depends(require_member)]):
    owner = UUID(principal["id"])
    with request.app.state.database.session() as db:
        owned(db, owner, session_id)
        answer = db.scalar(select(Message).where(Message.id == body.message_id,
                           Message.session_id == session_id, Message.role == "assistant"))
        if answer is None:
            raise HTTPException(404, "message_unavailable")
        question = db.scalar(select(Message).where(Message.session_id == session_id,
                             Message.turn_number == answer.turn_number, Message.role == "user"))
        text = " ".join(str(b.get("text", "")) for b in question.blocks) if question else ""
        engine = select_engine(text)
    if engine is None:
        return JSONResponse({"status": "ineligible"}, headers={"Cache-Control": "no-store"})
    gateway = request.app.state.gateway
    if not getattr(gateway, "available", True):
        raise HTTPException(503, "provider_unavailable")
    language = transient.response_language(owner, body.message_id)
    result = transient.run(owner, body.message_id, lambda: generate(gateway, engine, text, response_language=language),
                           start=body.start, limit=daily_usage_limit(principal, min(20, request.app.state.settings.llm_daily_request_limit)), background=True)
    return JSONResponse({**result, "engine": engine}, headers={"Cache-Control": "no-store"})
