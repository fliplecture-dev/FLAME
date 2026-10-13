"""Transactional answer request claims for B7 orchestration.

Call claim in a short transaction, execute the provider outside it, then finalize in
another transaction. A fencing token prevents an expired worker from committing.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from secrets import token_hex
from uuid import UUID, uuid4
from fastapi import HTTPException
from sqlalchemy import func, select
from app.modules.conversations.models import AnswerRequest, ConversationSession, Message
from app.modules.curriculum.catalogue import subject_path
from app.modules.curriculum.models import Curriculum
from app.modules.student_activity.models import ActivityEvent

LEASE = timedelta(seconds=90)
MAX_ATTEMPTS = 2

@dataclass(frozen=True)
class Claim:
    status: str
    request_id: UUID
    token: str | None = None
    result: dict | None = None

def payload_digest(body: dict) -> str:
    return sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def _context(db, row):
    if row.mode != "study":
        return
    data = row.context_snapshot
    curriculum = db.scalar(select(Curriculum).where(Curriculum.id == row.curriculum_id).with_for_update())
    if curriculum is None or curriculum.state != "published":
        raise HTTPException(409, "unavailable_context")
    try:
        subject_path(db, **{key: UUID(value) if value else None for key, value in data.items() if key.endswith("_id")})
    except HTTPException:
        raise HTTPException(409, "unavailable_context")
    if curriculum.revision != row.revision:
        raise HTTPException(409, "unavailable_context")

def claim(db, student_id: UUID, session_id: UUID, key: str, body: dict) -> Claim:
    """Atomically claim one logical question per session; caller commits."""
    if not key or len(key) > 255:
        raise HTTPException(422, "invalid_idempotency_key")
    row = db.scalar(select(ConversationSession).where(
        ConversationSession.id == session_id, ConversationSession.student_id == student_id).with_for_update())
    if row is None:
        raise HTTPException(404, "session_not_found")
    expected = {key: row.context_snapshot.get(key) for key in
                ("curriculum_id", "level_id", "subject_id", "domain_id",
                 "category_id", "topic_id", "subtopic_id")} if row.context_snapshot else None
    if row.mode != body.get("mode") or body.get("context") != expected:
        raise HTTPException(422, "session_context_mismatch")
    digest = payload_digest(body)
    existing = db.scalar(select(AnswerRequest).where(
        AnswerRequest.student_id == student_id, AnswerRequest.session_id == session_id,
        AnswerRequest.idempotency_key == key).with_for_update())
    now = datetime.now(timezone.utc)
    if existing and existing.payload_hash != digest:
        raise HTTPException(409, "idempotency_key_conflict")
    if existing and existing.status in ("completed", "failed"):
        return Claim(existing.status, existing.id, result=existing.result)
    _context(db, row)
    if existing:
        if existing.lease_expires_at and existing.lease_expires_at > now:
            raise HTTPException(409, "request_in_progress")
        if existing.attempts >= MAX_ATTEMPTS:
            existing.status = "failed"
            existing.result = {"status": "error", "code": "retry_exhausted"}
            existing.claim_token = None
            existing.lease_expires_at = None
            existing.updated_at = now
            return Claim("failed", existing.id, result=existing.result)
        request = existing
    else:
        other = db.scalar(select(AnswerRequest).where(
            AnswerRequest.session_id == session_id, AnswerRequest.status == "pending"))
        if other:
            raise HTTPException(409, "session_request_in_progress")
        request = AnswerRequest(student_id=student_id, session_id=session_id,
                                idempotency_key=key, payload_hash=digest, status="pending", attempts=0)
        db.add(request)
    token = token_hex(32)
    request.attempts += 1
    request.claim_token = token
    request.lease_expires_at = now + LEASE
    request.updated_at = now
    db.flush()
    return Claim("claimed", request.id, token=token)

def finalize(db, request_id: UUID, token: str, question: str, answer: dict, *, resolved=None,
             prompt_version=None, profile_version=None, model=None, input_tokens=None,
             output_tokens=None, latency_ms=None) -> dict:
    """Commit one user/assistant pair and answer result, or reject a stale worker."""
    request = db.scalar(select(AnswerRequest).where(AnswerRequest.id == request_id).with_for_update())
    if request is None or request.status != "pending" or request.claim_token != token:
        raise HTTPException(409, "request_claim_lost")
    session = db.scalar(select(ConversationSession).where(
        ConversationSession.id == request.session_id,
        ConversationSession.student_id == request.student_id).with_for_update())
    if session is None:
        raise HTTPException(404, "session_not_found")
    _context(db, session)
    number = (db.scalar(select(func.max(Message.turn_number)).where(Message.session_id == session.id)) or 0) + 1
    db.add(Message(session_id=session.id, turn_number=number, role="user",
                   blocks=[{"kind": "text", "text": question}]))
    assistant_id = uuid4()
    db.add(Message(id=assistant_id, session_id=session.id, turn_number=number, role="assistant",
                   blocks=answer["blocks"],
                   resolved_curriculum_id=resolved.ids["curriculum_id"] if resolved else None,
                   resolved_subject_id=resolved.ids["subject_id"] if resolved else None,
                   resolved_topic_id=resolved.ids["topic_id"] if resolved else None,
                   resolved_revision=resolved.revision if resolved else None))
    db.add(ActivityEvent(student_id=request.student_id, session_id=session.id,
                         event_type="question", deduplication_key="question:" + str(request.id),
                         path_snapshot=session.context_snapshot))
    answer = {**answer, "message_id": str(assistant_id)}
    request.status = "completed"
    request.result = answer
    request.prompt_version = prompt_version
    request.profile_version = profile_version
    request.model = model
    request.input_tokens = input_tokens
    request.output_tokens = output_tokens
    request.latency_ms = latency_ms
    request.claim_token = None
    request.lease_expires_at = None
    request.updated_at = datetime.now(timezone.utc)
    session.updated_at = request.updated_at
    session.recent_at = request.updated_at
    return answer

def fail(db, request_id: UUID, token: str, code: str) -> dict:
    """Terminal failures replay under the same key; retryable transport loss uses lease expiry."""
    request = db.scalar(select(AnswerRequest).where(AnswerRequest.id == request_id).with_for_update())
    if request is None or request.status != "pending" or request.claim_token != token:
        raise HTTPException(409, "request_claim_lost")
    request.status = "failed"
    request.result = {"status": "error", "code": code}
    request.claim_token = None
    request.lease_expires_at = None
    request.updated_at = datetime.now(timezone.utc)
    return request.result





def finish_unsupported(db, request_id: UUID, token: str, code: str, message: str) -> dict:
    """Store a non-generated capability outcome for exact-key replay."""
    request = db.scalar(select(AnswerRequest).where(AnswerRequest.id == request_id).with_for_update())
    if request is None or request.status != "pending" or request.claim_token != token:
        raise HTTPException(409, "request_claim_lost")
    request.status = "failed"
    request.result = {"status": "unsupported", "request_id": str(request.id),
                      "code": code, "message": message}
    request.claim_token = None
    request.lease_expires_at = None
    request.updated_at = datetime.now(timezone.utc)
    return request.result
