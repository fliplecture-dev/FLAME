"""B7 answer orchestration. Each database transaction ends before provider I/O."""
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from app.modules.conversations.models import AnswerRequest as StoredRequest, ConversationSession
from app.modules.conversations.requests import claim, fail, finalize, finish_unsupported
from app.modules.conversations.router import bounded_history, owned
from app.modules.curriculum.models import Level
from app.modules.identity.models import StudentProfile
from app.modules.teaching.capabilities import unsupported_capability
from app.modules.teaching.context import load_context
from app.modules.teaching.gateway import GatewayError
from app.modules.teaching.output_guard import has_forbidden_authority_claim
from app.modules.teaching.profiles import profile
from app.modules.teaching.prompt import assemble, assemble_open_curiosity
from app.modules.teaching.schemas import DirectAnswer, UnsupportedOutcome
from app.modules.recommendations.learning_need import INSTRUCTION, split_intent

MAX_ANSWER_CHARS = 6000


def _prepared(db, student_id: UUID, session_id: UUID, body):
    session = owned(db, student_id, session_id)
    history = bounded_history(db, student_id, session_id)
    if session.mode == "curiosity":
        return None, assemble_open_curiosity(body.question, history), None
    ids = {key: UUID(value) if value else None for key, value in session.context_snapshot.items()
           if key.endswith("_id")}
    context = load_context(db, ids, expected_revision=session.revision)
    level = db.get(Level, context.ids["level_id"])
    teaching = profile(level.code, level.name)
    return context, assemble(body.question, context, teaching, history), teaching.max_words


def _answer(request_id, context, generated, *, max_words: int | None = None):
    text = generated.text.strip()
    if not text or len(text) > MAX_ANSWER_CHARS or not isinstance(generated.input_tokens, int) or not isinstance(generated.output_tokens, int):
        raise GatewayError("invalid_provider_output")
    if max_words is not None and len(text.split()) > max_words:
        raise GatewayError("invalid_provider_output")
    if generated.input_tokens < 0 or generated.output_tokens < 0:
        raise GatewayError("invalid_provider_output")
    if any(ord(char) < 32 and char not in "\n\t" for char in text) or has_forbidden_authority_claim(text):
        raise GatewayError("invalid_provider_output")
    return DirectAnswer(response_id=uuid4(), request_id=request_id,
        curriculum_version=f"revision-{context.revision}" if context is not None else None,
        blocks=[{"id": str(uuid4()), "kind": "text", "text": text}]).model_dump(mode="json")


def ask(database, gateway, student_id: UUID, session_id: UUID, key: str, body, *, daily_limit: int = 100):
    canonical = body.model_dump(mode="json")
    unsupported = unsupported_capability(body.question)
    with database.session() as db, db.begin():
        # Serialize a member's quota across all owned sessions before creating a claim.
        db.scalar(select(StudentProfile).where(StudentProfile.id == student_id).with_for_update())
        existing = db.scalar(select(StoredRequest.id).where(
            StoredRequest.student_id == student_id, StoredRequest.session_id == session_id,
            StoredRequest.idempotency_key == key))
        if existing is None:
            count = db.scalar(select(func.count()).select_from(StoredRequest).where(
                StoredRequest.student_id == student_id,
                StoredRequest.created_at >= datetime.now(timezone.utc) - timedelta(days=1))) or 0
            if count >= daily_limit:
                raise HTTPException(429, "daily_limit_reached")
        claimed = claim(db, student_id, session_id, key, canonical)
        if claimed.status in ("completed", "failed"):
            return claimed.result
        if unsupported:
            outcome = finish_unsupported(db, claimed.request_id, claimed.token,
                                         unsupported.code, unsupported.message)
            return UnsupportedOutcome.model_validate(outcome).model_dump(mode="json")
        if not getattr(gateway, "available", True):
            raise HTTPException(503, "provider_unavailable")
        context, prompt, max_words = _prepared(db, student_id, session_id, body)
    started = perf_counter()
    try:
        messages = prompt.messages
        if context is not None:
            messages = [{"role": "system", "content": INSTRUCTION}, *messages]
        generated = gateway.generate(messages)
        answer_text, need = split_intent(generated.text)
        generated = replace(generated, text=answer_text)
        result = _answer(claimed.request_id, context, generated, max_words=max_words)
        if context is not None and need:
            result["learning_need"] = need
    except GatewayError as exc:
        with database.session() as db, db.begin():
            return fail(db, claimed.request_id, claimed.token, exc.code)
    except Exception:
        with database.session() as db, db.begin():
            return fail(db, claimed.request_id, claimed.token, "provider_unavailable")
    try:
        with database.session() as db, db.begin():
            # Study rechecks publication/revision after network I/O; open Curiosity has no path.
            if context is not None:
                load_context(db, context.ids, expected_revision=context.revision)
            return finalize(db, claimed.request_id, claimed.token, body.question, result,
                resolved=context, prompt_version=prompt.version + ("-intent1" if context else ""),
                profile_version=prompt.profile_version, model=generated.model,
                input_tokens=generated.input_tokens, output_tokens=generated.output_tokens,
                latency_ms=round((perf_counter() - started) * 1000))
    except HTTPException as exc:
        if exc.detail == "unavailable_context":
            with database.session() as db, db.begin():
                fail(db, claimed.request_id, claimed.token, "unavailable_context")
        raise
