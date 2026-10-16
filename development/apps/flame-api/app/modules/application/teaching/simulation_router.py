"""Owner-checked ephemeral source; saved text is independent of this extra provider call."""
from typing import Annotated
from uuid import UUID
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.modules.functional.conversations.models import Message, AnswerRequest
from app.modules.functional.conversations.router import owned
from app.modules.functional.identity.dependencies import require_member
from app.modules.functional.curriculum.teaching_context import load_context
from app.modules.decision_engine.visual.routing import decide_response_visual
from app.modules.application.teaching.visual_media import library_simulation
from app.modules.application.teaching.simulations import generate, transient
from app.modules.application.teaching.usage import daily_usage_limit

router = APIRouter(prefix="/api/v1")


class SimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    message_id: UUID
    start: bool = False


@router.post("/sessions/{session_id}/simulation")
def simulation(request: Request, session_id: UUID, body: SimulationRequest,
               principal: Annotated[dict, Depends(require_member)]):
    owner = UUID(principal["id"])
    config = request.app.state.settings
    with request.app.state.database.session() as db, db.begin():
        conversation = owned(db, owner, session_id, lock=True)
        answer = db.scalar(select(Message).where(Message.id == body.message_id,
                           Message.session_id == session_id, Message.role == "assistant"))
        if answer is None:
            raise HTTPException(404, "message_unavailable")
        question = db.scalar(select(Message).where(Message.session_id == session_id,
                             Message.turn_number == answer.turn_number, Message.role == "user"))
        text = " ".join(str(b.get("text", "")) for b in question.blocks) if question else ""
        stored = db.scalar(select(AnswerRequest).where(AnswerRequest.session_id == session_id,
                           AnswerRequest.result["message_id"].astext == str(body.message_id)))
        saved = (stored.result or {}) if stored is not None else {}
        routing = saved.get("visual_routing")
        if routing and routing["response_kind"] != "simulation":
            return JSONResponse({"status": "ineligible"}, headers={"Cache-Control": "no-store"})
        context = None
        if conversation.mode == "study":
            ids = {key: UUID(value) if value else None for key, value in conversation.context_snapshot.items() if key.endswith("_id")}
            context = load_context(db, ids, expected_revision=conversation.revision)
        routing = routing or decide_response_visual(text, mode=conversation.mode, context_names=context.names if context else None)
        if routing["response_kind"] != "simulation":
            return JSONResponse({"status": "ineligible"}, headers={"Cache-Control": "no-store"})
        language = routing.get("response_language") or transient.response_language(owner, body.message_id)
        # The saved plan resolves short follow-ups against owned answer history.
        # Reuse the same resolved topic for catalogue relevance and source generation.
        visual_question = routing.get("simulation_question") or text
        source = saved.get("simulation_source")
        if not source or source.get("kind") == "resource":
            media, selected = library_simulation(db, config, visual_question, context=context,
                saved_source=source if source else None, language=language)
            if media is not None:
                if stored is not None and not source:
                    stored.result = {**saved, "simulation_source": {**selected, "kind": "resource"}}
                return JSONResponse(media, headers={"Cache-Control": "no-store"})
        engine = source.get("engine") if source and source.get("kind") == "generated" else routing["simulation_engine"]
        if engine is not None and stored is not None and not source and body.start:
            stored.result = {**saved, "simulation_source": {"kind": "generated", "engine": engine}}
        generation_question = visual_question
        if context is not None:
            generation_question += "\nSelected learning topic (data): " + json.dumps(context.names, ensure_ascii=False)[:1500]
    if engine is None:
        return JSONResponse({"status": "ineligible"}, headers={"Cache-Control": "no-store"})
    gateway = request.app.state.gateway
    if not getattr(gateway, "available", True):
        raise HTTPException(503, "provider_unavailable")
    result = transient.run(owner, body.message_id, lambda: generate(gateway, engine, generation_question, response_language=language),
                           start=body.start, limit=daily_usage_limit(principal, min(20, request.app.state.settings.llm_daily_request_limit)), background=True)
    return JSONResponse({**result, "engine": result.get("engine", engine)}, headers={"Cache-Control": "no-store"})
