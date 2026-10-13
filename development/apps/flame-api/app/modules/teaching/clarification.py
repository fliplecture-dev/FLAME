"""Persistent, owned Curiosity clarification exchange for B7 to invoke."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.modules.conversations.models import PendingClarification
from app.modules.conversations.router import owned
from app.modules.teaching.context import TeachingContext, load_context
from app.modules.teaching.resolution import Resolution, resolve

TTL = timedelta(minutes=10)


@dataclass(frozen=True)
class Continuation:
    question: str
    context: TeachingContext


def create_pending(db, student_id: UUID, session_id: UUID, question: str,
                   resolution: Resolution) -> PendingClarification:
    session = owned(db, student_id, session_id, lock=True)
    if session.mode != "curiosity" or resolution.status != "clarification" or not resolution.candidates or len(resolution.candidates) > 8 or not question.strip() or len(question) > 4000:
        raise HTTPException(422, "invalid_clarification")
    db.query(PendingClarification).filter(
        PendingClarification.session_id == session_id,
        PendingClarification.status == "pending").update({"status": "cancelled"})
    candidates = [{"ids": {key: str(value) if value else None for key, value in item.ids.items()},
                   "revision": item.revision} for item in resolution.candidates]
    row = PendingClarification(student_id=student_id, session_id=session_id, question=question,
        candidates=candidates, status="pending", expires_at=datetime.now(timezone.utc) + TTL)
    db.add(row)
    db.flush()
    return row


def _ids(data):
    return {key: UUID(value) if value else None for key, value in data.items()}


def continue_pending(db, student_id: UUID, session_id: UUID, clarification_id: UUID,
                     *, subtopic_id: UUID | None = None, reply: str | None = None) -> Continuation:
    owned(db, student_id, session_id, lock=True)
    row = db.scalar(select(PendingClarification).where(
        PendingClarification.id == clarification_id,
        PendingClarification.student_id == student_id,
        PendingClarification.session_id == session_id).with_for_update())
    if row is None:
        raise HTTPException(404, "clarification_not_found")
    if row.status == "resolved" and row.selected_path:
        saved = next(item for item in row.candidates if item["ids"] == row.selected_path)
        if subtopic_id is not None and str(subtopic_id) != row.selected_path["subtopic_id"]:
            raise HTTPException(409, "clarification_already_resolved")
        context = load_context(db, _ids(row.selected_path), expected_revision=saved["revision"])
        return Continuation(row.question, context)
    if row.status != "pending":
        raise HTTPException(409, "clarification_unavailable")
    if row.expires_at < datetime.now(timezone.utc):
        raise HTTPException(409, "clarification_expired")
    if reply is not None and (not reply.strip() or len(reply) > 500):
        raise HTTPException(422, "clarification_reply_out_of_bounds")
    if (subtopic_id is None) == (reply is None):
        raise HTTPException(422, "clarification_choice_required")
    selected = None
    if subtopic_id is not None:
        selected = next((item for item in row.candidates
                         if item["ids"]["subtopic_id"] == str(subtopic_id)), None)
    elif reply:
        answer = reply.casefold().strip()
        ordinal = {"first": 0, "1": 0, "second": 1, "2": 1, "third": 2, "3": 2,
                   "fourth": 3, "4": 3, "fifth": 4, "5": 4, "sixth": 5, "6": 5,
                   "seventh": 6, "7": 6, "eighth": 7, "8": 7}
        index = ordinal.get(answer.replace("the ", "").replace(" one", ""))
        if index is not None and index < len(row.candidates):
            selected = row.candidates[index]
        else:
            contexts = [load_context(db, _ids(item["ids"]), expected_revision=item["revision"])
                        for item in row.candidates]
            result = resolve(reply, contexts)
            if result.status == "resolved":
                selected = next(item for item in row.candidates
                                if item["ids"]["subtopic_id"] == str(result.context.ids["subtopic_id"]))
    if selected is None:
        raise HTTPException(422, "clarification_choice_unclear")
    context = load_context(db, _ids(selected["ids"]), expected_revision=selected["revision"])
    row.selected_path = selected["ids"]
    row.status = "resolved"
    return Continuation(row.question, context)


def cancel_pending(db, student_id: UUID, session_id: UUID) -> None:
    owned(db, student_id, session_id, lock=True)
    db.query(PendingClarification).filter(PendingClarification.student_id == student_id,
        PendingClarification.session_id == session_id, PendingClarification.status == "pending").update(
            {"status": "cancelled"})




