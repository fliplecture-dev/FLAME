"""Owned B6 school-topic gate with idempotent, paginated history."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, tuple_

from app.modules.conversations.models import PendingClarification
from app.modules.conversations.router import decode_cursor, encode_cursor, owned
from app.modules.identity.dependencies import require_member
from app.modules.teaching.clarification import create_pending, continue_pending
from app.modules.teaching.context import load_context
from app.modules.teaching.models import TopicCheckEvent
from app.modules.teaching.resolution import Resolution
from app.modules.teaching.schemas import (
    ClarificationCandidate, ClarificationContinuation, ClarificationOutcome, OutOfScopeOutcome,
)
from app.modules.teaching.service import prepare

router = APIRouter(prefix="/api/v1")
Member = Annotated[dict, Depends(require_member)]


class TopicCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=4000)


def candidate(context):
    names, ids = context.names, context.ids
    return ClarificationCandidate(**ids,
        curriculum=names["curriculum"], level=names["level"], subject=names["subject"],
        domain=names["domain"], topic=names["topic"], subtopic=names["subtopic"],
        revision=context.revision)


def ready(context, question, request_id):
    return {"status": "ready", "request_id": str(request_id), "question": question,
            "context": candidate(context).model_dump(mode="json"),
            "answer_available": True}


def clarification(row, contexts, request_id):
    return ClarificationOutcome(request_id=request_id, clarification_id=row.id,
        question=row.question, candidates=[candidate(item) for item in contexts],
        expires_at=row.expires_at).model_dump(mode="json")


def _choice_digest(body):
    data = {"subtopic_id": str(body.subtopic_id) if body.subtopic_id else None,
            "reply": body.reply.strip().casefold() if body.reply else None}
    return sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _event_data(row, db):
    status, response = row.status, row.response
    if status == "clarification":
        pending = db.get(PendingClarification, row.clarification_id)
        if pending is None or pending.status != "pending" or pending.expires_at <= datetime.now(timezone.utc):
            status = "expired" if pending and pending.expires_at <= datetime.now(timezone.utc) else "cancelled"
            response = {"status": status, "request_id": str(row.id),
                        "message": "This topic choice is no longer available. Check the topic again."}
    return {"id": str(row.id), "question": row.question, "status": status,
            "response": response, "created_at": row.created_at.isoformat()}


def _cancel_pending(db, student_id, session_id):
    pending = db.scalars(select(PendingClarification).where(
        PendingClarification.student_id == student_id,
        PendingClarification.session_id == session_id,
        PendingClarification.status == "pending").with_for_update()).all()
    for row in pending:
        row.status = "cancelled"
        event = db.scalar(select(TopicCheckEvent).where(
            TopicCheckEvent.clarification_id == row.id).with_for_update())
        if event:
            event.status = "cancelled"
            event.response = {"status": "cancelled", "request_id": str(event.id),
                              "message": "This topic choice was replaced by a new question."}


@router.post("/sessions/{session_id}/topic-check")
def check_topic(request: Request, session_id: UUID, body: TopicCheck, principal: Member,
                idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]):
    student_id = UUID(principal["id"])
    if not idempotency_key.strip() or len(idempotency_key) > 255:
        raise HTTPException(422, "invalid_idempotency_key")
    question = body.question.strip()
    digest = sha256(question.encode("utf-8")).hexdigest()
    with request.app.state.database.session() as db, db.begin():
        session = owned(db, student_id, session_id, lock=True)
        existing = db.scalar(select(TopicCheckEvent).where(
            TopicCheckEvent.student_id == student_id,
            TopicCheckEvent.session_id == session_id,
            TopicCheckEvent.idempotency_key == idempotency_key).with_for_update())
        if existing:
            if existing.payload_hash != digest:
                raise HTTPException(409, "idempotency_key_conflict")
            if existing.status == "ready" and existing.context_snapshot:
                ids = {key: UUID(value) if value else None
                       for key, value in existing.context_snapshot.items() if key.endswith("_id")}
                load_context(db, ids, expected_revision=existing.context_snapshot["revision"])
            return _event_data(existing, db)["response"]
        _cancel_pending(db, student_id, session_id)
        session.updated_at = datetime.now(timezone.utc)
        result = prepare(db, student_id, session_id, question)
        event_id = uuid4()
        if result.status == "ready":
            response = ready(result.context, question, event_id)
            status, pending_id, context_snapshot = "ready", None, response["context"]
        elif result.status == "out_of_scope":
            response = OutOfScopeOutcome(request_id=event_id).model_dump(mode="json")
            status, pending_id, context_snapshot = "out_of_scope", None, None
        elif result.status == "clarification":
            pending = create_pending(db, student_id, session_id, question,
                Resolution("clarification", None, result.candidates))
            response = clarification(pending, result.candidates, event_id)
            status, pending_id, context_snapshot = "clarification", pending.id, None
        else:
            raise HTTPException(503, "topic_resolution_unavailable")
        db.add(TopicCheckEvent(id=event_id, student_id=student_id, session_id=session_id,
            idempotency_key=idempotency_key, payload_hash=digest, question=question,
            status=status, clarification_id=pending_id, context_snapshot=context_snapshot,
            response=response, created_at=datetime.now(timezone.utc)))
        return response


@router.get("/sessions/{session_id}/topic-check")
def current_clarification(request: Request, session_id: UUID, principal: Member):
    student_id = UUID(principal["id"])
    with request.app.state.database.session() as db:
        session = owned(db, student_id, session_id)
        if session.mode != "curiosity":
            return {"pending": None}
        row = db.scalar(select(PendingClarification).where(
            PendingClarification.student_id == student_id,
            PendingClarification.session_id == session_id,
            PendingClarification.status == "pending",
            PendingClarification.expires_at > datetime.now(timezone.utc))
            .order_by(PendingClarification.created_at.desc()))
        if row is None:
            return {"pending": None}
        try:
            for item in row.candidates:
                load_context(db, {key: UUID(value) if value else None
                             for key, value in item["ids"].items()},
                             expected_revision=item["revision"])
        except HTTPException:
            return {"pending": None}
        event = db.scalar(select(TopicCheckEvent).where(
            TopicCheckEvent.clarification_id == row.id))
        return {"pending": event.response if event else None}


@router.get("/sessions/{session_id}/topic-check/history")
def topic_history(request: Request, session_id: UUID, principal: Member,
                  cursor: str | None = None, limit: int = Query(25, ge=1, le=100)):
    student_id = UUID(principal["id"])
    point = decode_cursor(cursor)
    with request.app.state.database.session() as db:
        owned(db, student_id, session_id)
        query = select(TopicCheckEvent).where(
            TopicCheckEvent.student_id == student_id,
            TopicCheckEvent.session_id == session_id)
        if point:
            query = query.where(tuple_(TopicCheckEvent.created_at, TopicCheckEvent.id) < point)
        rows = db.scalars(query.order_by(
            TopicCheckEvent.created_at.desc(), TopicCheckEvent.id.desc()).limit(limit + 1)).all()
        return {"items": [_event_data(row, db) for row in rows[:limit]],
                "next_cursor": encode_cursor(rows[limit - 1], "created_at")
                               if len(rows) > limit else None}


@router.post("/sessions/{session_id}/clarifications/{clarification_id}")
def choose_topic(request: Request, session_id: UUID, clarification_id: UUID,
                 body: ClarificationContinuation, principal: Member):
    if body.clarification_id != clarification_id:
        raise HTTPException(422, "clarification_id_mismatch")
    student_id = UUID(principal["id"])
    choice_hash = _choice_digest(body)
    with request.app.state.database.session() as db, db.begin():
        owned(db, student_id, session_id, lock=True)
        event = db.scalar(select(TopicCheckEvent).where(
            TopicCheckEvent.student_id == student_id,
            TopicCheckEvent.session_id == session_id,
            TopicCheckEvent.clarification_id == clarification_id).with_for_update())
        if event is None:
            raise HTTPException(404, "clarification_not_found")
        if event.choice_hash:
            if event.choice_hash != choice_hash:
                raise HTTPException(409, "clarification_already_resolved")
            ids = {key: UUID(value) if value else None
                   for key, value in event.context_snapshot.items() if key.endswith("_id")}
            load_context(db, ids, expected_revision=event.context_snapshot["revision"])
            return event.response
        if event.status != "clarification":
            raise HTTPException(409, "clarification_unavailable")
        selected = continue_pending(db, student_id, session_id, clarification_id,
                                    subtopic_id=body.subtopic_id, reply=body.reply)
        response = ready(selected.context, selected.question, event.id)
        session = owned(db, student_id, session_id, lock=True)
        session.updated_at = datetime.now(timezone.utc)
        event.status = "ready"
        event.choice_hash = choice_hash
        event.context_snapshot = response["context"]
        event.response = response
        return response



