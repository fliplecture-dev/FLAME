"""Owned sessions, history, and measured activity."""
import base64
import binascii
import json
from datetime import datetime, timezone
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import case, func, select, tuple_, update
from sqlalchemy.dialects.postgresql import insert
from app.modules.functional.conversations.models import ConversationSession, Message, AnswerRequest, PendingClarification
from app.modules.functional.conversations.topic_checks import TopicCheckEvent
from app.modules.functional.curriculum.catalogue import subject_path
from app.modules.functional.curriculum.models import Curriculum, Level, Subject, Domain, Category, Topic, Subtopic
from app.modules.functional.identity.dependencies import require_member, require_admin
from app.modules.functional.identity.models import StudentProfile
from app.modules.functional.student_activity.models import ActivityEvent
from app.modules.functional.recommendation_history.service import remove_for_sessions

router = APIRouter(prefix="/api/v1")
Member = Annotated[dict, Depends(require_member)]
Admin = Annotated[dict, Depends(require_admin)]
PATH = ("curriculum_id", "level_id", "subject_id", "domain_id", "category_id", "topic_id", "subtopic_id")

class Context(BaseModel):
    model_config = ConfigDict(extra="forbid")
    curriculum_id: UUID
    level_id: UUID
    subject_id: UUID
    domain_id: UUID
    category_id: UUID | None = None
    topic_id: UUID
    subtopic_id: UUID | None = None

class CreateSession(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["study", "curiosity"]
    context: Context | None = None
    @model_validator(mode="after")
    def valid(self):
        if (self.mode == "study") != (self.context is not None):
            raise ValueError("Study requires context; Curiosity forbids it")
        return self

class PinSession(BaseModel):
    model_config = ConfigDict(extra="forbid")
    pinned: bool

class Confirm(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirm: Literal[True]

class RecordActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: Literal["visit"]
    deduplication_key: str = Field(min_length=8, max_length=255)
    session_id: UUID | None = None

def owned(db, student_id, session_id, lock=False):
    query = select(ConversationSession).where(ConversationSession.id == session_id, ConversationSession.student_id == student_id)
    row = db.scalar(query.with_for_update() if lock else query)
    if row is None:
        raise HTTPException(404, "session_not_found")
    return row

def snapshot(db, context):
    curriculum = db.scalar(select(Curriculum).where(Curriculum.id == context.curriculum_id).with_for_update())
    if curriculum is None or curriculum.state != "published": raise HTTPException(404, "curriculum_not_found")
    ids = context.model_dump()
    subject_path(db, **ids)
    names = {}
    for key, cls in zip(PATH, (Curriculum, Level, Subject, Domain, Category, Topic, Subtopic)):
        names[key[:-3]] = db.get(cls, ids[key]).name if ids[key] else None
    return {**{k: str(v) if v else None for k, v in ids.items()}, "names": names}

def session_data(row):
    return {"id": str(row.id), "mode": row.mode, "context": row.context_snapshot,
            "revision": row.revision, "pinned": row.pinned,
            "recent_at": row.recent_at.isoformat() if row.recent_at else None, "created_at": row.created_at.isoformat(),
            "updated_at": row.updated_at.isoformat()}

def message_data(row, request_id=None):
    return {"id": str(row.id), "turn_number": row.turn_number, "role": row.role,
            "blocks": row.blocks, "created_at": row.created_at.isoformat(),
            "request_id": str(request_id) if request_id else None}

def decode_cursor(value):
    if value is None: return None
    try:
        stamp, identifier = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
        moment = datetime.fromisoformat(stamp)
        if moment.tzinfo is None: raise ValueError("timezone required")
        return moment, UUID(identifier)
    except (ValueError, TypeError, IndexError, binascii.Error):
        raise HTTPException(422, "invalid_cursor")

def encode_cursor(row, field):
    return base64.urlsafe_b64encode(json.dumps([getattr(row, field).isoformat(), str(row.id)]).encode()).decode().rstrip("=")

def decode_message_cursor(value):
    if value is None: return None
    try:
        number, role_index, identifier = json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))
        if type(number) is not int or number < 1 or type(role_index) is not int or role_index not in (0, 1):
            raise ValueError("invalid message cursor")
        return number, role_index, UUID(identifier)
    except (ValueError, TypeError, IndexError, binascii.Error):
        raise HTTPException(422, "invalid_cursor")

def encode_message_cursor(row):
    value = [row.turn_number, 1 if row.role == "assistant" else 0, str(row.id)]
    return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
def bounded_history(db, student_id, session_id, max_turns=8, max_chars=12000):
    """For B6/B7: only owned complete pairs, within a strict character budget."""
    owned(db, student_id, session_id)
    rows = db.scalars(select(Message).where(Message.session_id == session_id)
                      .order_by(Message.turn_number.desc(), Message.role.desc()).limit(max_turns * 2)).all()
    pairs = {}
    for row in rows: pairs.setdefault(row.turn_number, {})[row.role] = row
    result, budget = [], max_chars
    for number in sorted(pairs, reverse=True):
        pair = pairs[number]
        if "user" not in pair or "assistant" not in pair: continue
        size = len(json.dumps([pair["user"].blocks, pair["assistant"].blocks]))
        if size > budget: break
        budget -= size
        result.append({"turn_number": number, "user": pair["user"].blocks, "assistant": pair["assistant"].blocks})
    return list(reversed(result))

@router.post("/sessions", status_code=201)
def create_session(request: Request, body: CreateSession, principal: Member):
    student_id = UUID(principal["id"])
    with request.app.state.database.session() as db, db.begin():
        now = datetime.now(timezone.utc)
        profile = db.scalar(select(StudentProfile).where(StudentProfile.id == student_id).with_for_update())
        if profile is None or profile.status != "active": raise HTTPException(403, "account_inactive")
        if body.context:
            data = snapshot(db, body.context)
            curriculum = db.get(Curriculum, body.context.curriculum_id)
            existing = db.scalar(select(ConversationSession).where(
                ConversationSession.student_id == student_id,
                ConversationSession.mode == "study",
                ConversationSession.curriculum_id == curriculum.id,
                ConversationSession.revision == curriculum.revision,
                ConversationSession.context_snapshot.contains({key: data[key] for key in PATH}),
            ).order_by(ConversationSession.updated_at.desc()).limit(1))
            if existing is not None:
                existing.recent_at = now
                return session_data(existing)
            row = ConversationSession(student_id=student_id, mode="study",
                curriculum_id=curriculum.id, revision=curriculum.revision, context_snapshot=data,
                created_at=now, updated_at=now, recent_at=now)
        else:
            row = ConversationSession(student_id=student_id, mode="curiosity", created_at=now, updated_at=now, recent_at=now)
        db.add(row); db.flush()
        db.add(ActivityEvent(student_id=student_id, session_id=row.id, event_type="session_started",
            path_snapshot=row.context_snapshot, deduplication_key="session:" + str(row.id)))
        return session_data(row)

@router.get("/sessions")
def list_sessions(request: Request, principal: Member, cursor: str | None = None, limit: int = Query(25, ge=1, le=100)):
    point = decode_cursor(cursor)
    with request.app.state.database.session() as db:
        q = select(ConversationSession).where(ConversationSession.student_id == UUID(principal["id"]))
        if point: q = q.where(tuple_(ConversationSession.updated_at, ConversationSession.id) < point)
        rows = db.scalars(q.order_by(ConversationSession.updated_at.desc(), ConversationSession.id.desc()).limit(limit + 1)).all()
        page = rows[:limit]
        first_questions = {}
        if page:
            messages = db.scalars(select(Message).where(
                Message.session_id.in_([row.id for row in page]),
                Message.role == "user", Message.turn_number == 1)).all()
            first_questions = {message.session_id: next((block.get("text", "") for block in message.blocks
                if block.get("kind") == "text"), "") for message in messages}
        return {"items": [{**session_data(row), "first_question": first_questions.get(row.id, "")} for row in page],
                "next_cursor": encode_cursor(rows[limit - 1], "updated_at") if len(rows) > limit else None}

@router.post("/sessions/recent/clear")
def clear_recent_history(request: Request, body: Confirm, principal: Member):
    with request.app.state.database.session() as db, db.begin():
        db.execute(update(ConversationSession).where(
            ConversationSession.student_id == UUID(principal["id"]),
            ConversationSession.pinned.is_(False),
        ).values(recent_at=None))
    return {"status": "cleared"}


@router.post("/sessions/pins/clear")
def unpin_all_sessions(request: Request, body: Confirm, principal: Member):
    with request.app.state.database.session() as db, db.begin():
        db.execute(update(ConversationSession).where(
            ConversationSession.student_id == UUID(principal["id"]),
            ConversationSession.pinned.is_(True),
        ).values(pinned=False, recent_at=datetime.now(timezone.utc)))
    return {"status": "unpinned"}


@router.post("/sessions/{session_id}/recent")
def open_conversation(request: Request, session_id: UUID, body: Confirm, principal: Member):
    with request.app.state.database.session() as db, db.begin():
        row = owned(db, UUID(principal["id"]), session_id, lock=True)
        row.recent_at = datetime.now(timezone.utc)
        return session_data(row)


@router.get("/sessions/{session_id}")
def get_session(request: Request, session_id: UUID, principal: Member):
    with request.app.state.database.session() as db:
        return session_data(owned(db, UUID(principal["id"]), session_id))

@router.get("/sessions/{session_id}/messages")
def list_messages(request: Request, session_id: UUID, principal: Member, cursor: str | None = None, limit: int = Query(25, ge=1, le=100)):
    point = decode_message_cursor(cursor)
    with request.app.state.database.session() as db:
        owned(db, UUID(principal["id"]), session_id)
        q = select(Message).where(Message.session_id == session_id)
        role_index = case((Message.role == "assistant", 1), else_=0)
        if point: q = q.where(tuple_(Message.turn_number, role_index, Message.id) < point)
        rows = db.scalars(q.order_by(Message.turn_number.desc(), role_index.desc(), Message.id.desc()).limit(limit + 1)).all()
        page = rows[:limit]
        assistant_ids = [str(row.id) for row in page if row.role == "assistant"]
        references = dict(db.execute(select(AnswerRequest.result["message_id"].astext, AnswerRequest.id).where(
            AnswerRequest.student_id == UUID(principal["id"]), AnswerRequest.session_id == session_id,
            AnswerRequest.status == "completed", AnswerRequest.result["message_id"].astext.in_(assistant_ids))).all()) if assistant_ids else {}
        return {"items": [message_data(x, references.get(str(x.id))) for x in page],
                "next_cursor": encode_message_cursor(rows[limit - 1]) if len(rows) > limit else None}

@router.patch("/sessions/{session_id}/pin")
def pin_session(request: Request, session_id: UUID, body: PinSession, principal: Member):
    with request.app.state.database.session() as db, db.begin():
        row = owned(db, UUID(principal["id"]), session_id, lock=True)
        row.pinned = body.pinned
        if row.recent_at is None:
            row.recent_at = datetime.now(timezone.utc)
        return session_data(row)

@router.delete("/sessions/{session_id}")
def delete_session(request: Request, session_id: UUID, body: Confirm, principal: Member):
    with request.app.state.database.session() as db, db.begin():
        row = owned(db, UUID(principal["id"]), session_id, lock=True)
        db.query(TopicCheckEvent).filter(TopicCheckEvent.session_id == row.id).delete(synchronize_session=False)
        db.query(PendingClarification).filter(PendingClarification.session_id == row.id).delete(synchronize_session=False)
        remove_for_sessions(db, [row.id])
        db.query(Message).filter(Message.session_id == row.id).delete(synchronize_session=False)
        db.query(AnswerRequest).filter(AnswerRequest.session_id == row.id).delete(synchronize_session=False)
        db.query(ActivityEvent).filter(ActivityEvent.session_id == row.id).delete(synchronize_session=False)
        db.delete(row)
    return {"status": "deleted", "session_id": str(session_id)}

@router.post("/me/activity", status_code=201)
def record_activity(request: Request, body: RecordActivity, principal: Member):
    student_id = UUID(principal["id"])
    with request.app.state.database.session() as db, db.begin():
        profile = db.scalar(select(StudentProfile).where(StudentProfile.id == student_id).with_for_update())
        if profile is None or profile.status != "active": raise HTTPException(403, "account_inactive")
        if body.session_id: owned(db, student_id, body.session_id)
        inserted = db.scalar(insert(ActivityEvent).values(student_id=student_id,
            session_id=body.session_id, event_type=body.event_type,
            deduplication_key=body.deduplication_key).on_conflict_do_nothing(
                index_elements=["student_id", "deduplication_key"]).returning(ActivityEvent.id))
        return {"recorded": inserted is not None}

@router.get("/admin/students/{student_id}/activity")
def admin_activity(request: Request, student_id: UUID, _: Admin):
    with request.app.state.database.session() as db:
        profile = db.get(StudentProfile, student_id)
        if profile is None or profile.status in ("deleted", "deleting"): raise HTTPException(404, "student_not_found")
        counts = dict(db.execute(select(ActivityEvent.event_type, func.count()).where(
            ActivityEvent.student_id == student_id).group_by(ActivityEvent.event_type)).all())
        sessions = db.scalar(select(func.count()).select_from(ConversationSession).where(
            ConversationSession.student_id == student_id)) or 0
        questions = db.scalar(select(func.count()).select_from(Message).join(
            ConversationSession, Message.session_id == ConversationSession.id).where(
                ConversationSession.student_id == student_id, Message.role == "user")) or 0
        last = db.scalar(select(func.max(ActivityEvent.created_at)).where(ActivityEvent.student_id == student_id))
        return {"student_id": str(student_id), "visits": counts.get("visit", 0),
                "sessions": sessions, "questions": questions, "resource_opens": counts.get("resource_open", 0),
                "last_activity_at": last.isoformat() if last else None}

@router.delete("/me")
def delete_account(request: Request, body: Confirm, principal: Member):
    """Remove FLAME-owned private rows and revoke every browser session in one transaction."""
    from datetime import datetime, timezone
    from app.modules.functional.data_lifecycle.models import DeletionRequest
    from app.modules.functional.data_lifecycle.service import complete_provider_deletion
    from app.modules.functional.identity.models import AdminRole, BrowserSession
    from app.modules.functional.learning.models import LearningMembership
    student_id = UUID(principal["id"])
    settings = request.app.state.settings
    if not settings.supabase_url or not (settings.supabase_secret_key or settings.supabase_service_role_key):
        raise HTTPException(503, "account_deletion_unavailable")
    with request.app.state.database.session() as db, db.begin():
        profile = db.scalar(select(StudentProfile).where(StudentProfile.id == student_id).with_for_update())
        if profile is None or profile.status != "active":
            raise HTTPException(404, "profile_not_found")
        session_ids = db.scalars(select(ConversationSession.id).where(
            ConversationSession.student_id == student_id)).all()
        if session_ids:
            remove_for_sessions(db, session_ids)
            db.query(Message).filter(Message.session_id.in_(session_ids)).delete(synchronize_session=False)
        db.query(TopicCheckEvent).filter(TopicCheckEvent.student_id == student_id).delete(synchronize_session=False)
        db.query(PendingClarification).filter(PendingClarification.student_id == student_id).delete(synchronize_session=False)
        db.query(AnswerRequest).filter(AnswerRequest.student_id == student_id).delete(synchronize_session=False)
        db.query(ActivityEvent).filter(ActivityEvent.student_id == student_id).delete(synchronize_session=False)
        db.query(ConversationSession).filter(ConversationSession.student_id == student_id).delete(synchronize_session=False)
        db.query(LearningMembership).filter(LearningMembership.student_id == student_id).delete(synchronize_session=False)
        db.query(AdminRole).filter(AdminRole.auth_subject == profile.auth_subject).delete(synchronize_session=False)
        db.query(BrowserSession).filter(BrowserSession.auth_subject == profile.auth_subject).delete(
            synchronize_session=False)
        profile.display_name = None
        profile.email = None
        profile.status = "deleting"
        receipt = DeletionRequest(student_id=student_id, status="pending_provider")
        db.add(receipt)
        db.flush()
    if complete_provider_deletion(request.app.state.database, settings, receipt.id):
        return {"status": "deleted", "deletion_request_id": str(receipt.id)}
    return JSONResponse(status_code=202, content={"status": "pending_provider",
        "deletion_request_id": str(receipt.id)})














