"""Authenticated, owned answer transport."""
from typing import Annotated
from uuid import UUID
import json
import logging
from queue import Queue, Empty
from threading import Thread, Event
from time import monotonic
from fastapi.responses import StreamingResponse
from app.modules.application.teaching.gateway import GatewayError

from fastapi import APIRouter, Depends, Header, HTTPException, Request

from app.core.errors import error_response
from app.modules.functional.identity.dependencies import require_member
from app.modules.functional.conversations.router import owned
from pydantic import BaseModel, ConfigDict, Field
from app.modules.application.learning_response.service import ask
from app.modules.decision_engine.teaching.capabilities import unsupported_capability
from app.modules.application.teaching.schemas import AnswerRequest
from app.modules.application.teaching.usage import daily_usage_limit

router = APIRouter(prefix="/api/v1")
Member = Annotated[dict, Depends(require_member)]

class CapabilityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=4000)

@router.post("/sessions/{session_id}/capability-check")
def check_capability(request: Request, session_id: UUID, body: CapabilityCheck, principal: Member):
    with request.app.state.database.session() as db:
        owned(db, UUID(principal["id"]), session_id)
    unsupported = unsupported_capability(body.question)
    return ({"status": "unsupported", "code": unsupported.code, "message": unsupported.message}
            if unsupported else {"status": "continue"})

@router.post("/sessions/{session_id}/ask")
def ask_question(request: Request, session_id: UUID, body: AnswerRequest, principal: Member,
                 idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]):
    if not getattr(request.app.state.gateway, "available", True) and not unsupported_capability(body.question):
        return error_response(request, 503, "provider_unavailable",
                              "Learning answers are unavailable right now.", retryable=True)
    result = ask(request.app.state.database, request.app.state.gateway,
                 UUID(principal["id"]), session_id, idempotency_key, body,
                 daily_limit=daily_usage_limit(principal, request.app.state.settings.llm_daily_request_limit))
    if result["status"] == "error":
        code = result["code"]
        status = (429 if code in ("daily_limit_reached", "provider_rate_limited", "provider_budget_exceeded")
                  else 409 if code == "unavailable_context" else 503)
        return error_response(request, status, code,
                              "The answer could not be completed. Start a new request to try again.",
                              retryable=False)
    return result


@router.post("/sessions/{session_id}/ask-stream")
def ask_stream(request: Request, session_id: UUID, body: AnswerRequest, principal: Member,
               idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]):
    # Check ownership before opening the stream; ask still enforces quota/idempotency/context.
    owner = UUID(principal["id"])
    with request.app.state.database.session() as db:
        owned(db, owner, session_id)
    queue, cancelled = Queue(maxsize=256), Event()
    def delta(value):
        if cancelled.is_set():
            raise GatewayError("provider_unavailable")
        # Bounded transport queue; a slow/disconnected consumer cannot grow memory forever.
        try:
            queue.put({"type": "delta", "text": value}, timeout=1)
        except Exception:
            raise GatewayError("provider_unavailable") from None
    def work():
        try:
            result = ask(request.app.state.database, request.app.state.gateway, owner,
                         session_id, idempotency_key, body,
                         daily_limit=daily_usage_limit(principal, request.app.state.settings.llm_daily_request_limit), on_delta=delta)
            event = {"type": "answer", "answer": result}
        except HTTPException as exc:
            # Preserve safe operational rejections after the HTTP stream opens.
            # Never send arbitrary exception details or private inputs to clients.
            detail = exc.detail.get("code") if isinstance(exc.detail, dict) else exc.detail
            allowed = {"daily_limit_reached", "request_in_progress", "session_request_in_progress",
                       "unavailable_context", "session_context_mismatch", "idempotency_key_conflict",
                       "provider_unavailable", "catalogue_item_unavailable", "catalogue_context_too_large"}
            code = detail if isinstance(detail, str) and detail in allowed else "answer_unavailable"
            event = {"type": "failure", "code": code, "status": exc.status_code}
            logging.getLogger("flame").warning("answer_stream_rejected", extra={"fields": {
                "code": code, "status": exc.status_code,
                "request_id": getattr(request.state, "request_id", None)}})
        except Exception:
            event = {"type": "failure", "code": "answer_unavailable"}
        if not cancelled.is_set():
            try:
                queue.put(event, timeout=1)
            except Exception:
                pass
    def events():
        Thread(target=work, daemon=True).start()
        started = monotonic()
        try:
            while True:
                if monotonic() - started > 40:
                    yield '{"type":"failure","code":"answer_timeout"}\n'
                    break
                try:
                    event = queue.get(timeout=1)
                except Empty:
                    yield '{"type":"heartbeat"}\n'
                    continue
                yield json.dumps(event, ensure_ascii=False) + "\n"
                if event["type"] in {"answer", "failure"}:
                    break
        finally:
            cancelled.set()
    return StreamingResponse(events(), media_type="application/x-ndjson",
                             headers={"Cache-Control": "no-store", "X-Accel-Buffering": "no"})

