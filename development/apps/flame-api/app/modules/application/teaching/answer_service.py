"""B7 answer orchestration. Each database transaction ends before provider I/O."""
from datetime import datetime, timedelta, timezone
from dataclasses import replace
from time import perf_counter
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from app.modules.functional.conversations.models import AnswerRequest as StoredRequest, ConversationSession
from app.modules.functional.conversations.requests import claim, fail, finalize, finish_unsupported
from app.modules.functional.conversations.router import bounded_history, owned
from app.modules.functional.curriculum.models import Level
from app.modules.functional.identity.models import StudentProfile
from app.modules.functional.discovery.service import detail as catalogue_detail
from app.modules.application.teaching.catalogue_context import with_listing
from app.modules.decision_engine.teaching.capabilities import unsupported_capability
from app.modules.functional.curriculum.teaching_context import load_context
from app.modules.application.teaching.gateway import GatewayError
from app.modules.decision_engine.teaching.output_guard import has_forbidden_authority_claim
from app.modules.decision_engine.teaching.profiles import profile
from app.modules.application.teaching.prompt import assemble, assemble_open_curiosity
from app.modules.application.teaching.schemas import DirectAnswer, UnsupportedOutcome
from app.modules.application.teaching.rich_answer import parse_blocks, readable
from app.modules.application.teaching.math_visuals import apply_decision, TEMPLATES
from app.modules.application.teaching.simulations import transient
from app.modules.decision_engine.recommendation.learning_need import INSTRUCTION, split_intent

from app.modules.application.teaching.usage import quota_day_start

MAX_ANSWER_CHARS = 6000


def _prepared(db, student_id: UUID, session_id: UUID, body):
    session = owned(db, student_id, session_id)
    history = bounded_history(db, student_id, session_id)
    if session.mode == "curiosity":
        return None, assemble_open_curiosity(body.question, history, response_language=body.response_language), None
    ids = {key: UUID(value) if value else None for key, value in session.context_snapshot.items()
           if key.endswith("_id")}
    context = load_context(db, ids, expected_revision=session.revision)
    level = db.get(Level, context.ids["level_id"])
    teaching = profile(level.code, level.name)
    return context, assemble(body.question, context, teaching, history, response_language=body.response_language), teaching.max_words


def _answer(request_id, context, generated, *, max_words: int | None = None, rendering_decision: dict | None = None):
    text = generated.text.strip()
    if not text or len(text) > MAX_ANSWER_CHARS or not isinstance(generated.input_tokens, int) or not isinstance(generated.output_tokens, int):
        raise GatewayError("invalid_provider_output")
    blocks = parse_blocks(text)
    if rendering_decision is not None:
        blocks = apply_decision(blocks, rendering_decision)
    visible = readable(blocks)
    if max_words is not None and len(visible.split()) > max_words:
        raise GatewayError("invalid_provider_output")
    if generated.input_tokens < 0 or generated.output_tokens < 0:
        raise GatewayError("invalid_provider_output")
    if any(ord(char) < 32 and char not in "\n\t" for char in visible) or has_forbidden_authority_claim(visible):
        raise GatewayError("invalid_provider_output")
    return DirectAnswer(response_id=uuid4(), request_id=request_id,
        curriculum_version=f"revision-{context.revision}" if context is not None else None,
        blocks=blocks).model_dump(mode="json")


def ask(database, gateway, student_id: UUID, session_id: UUID, key: str, body, *, daily_limit: int | None = 25, on_delta=None):
    canonical = body.model_dump(mode="json")
    # Preserve hashes for pre-language-selector requests when Auto is selected.
    if canonical.get("response_language") is None:
        canonical.pop("response_language", None)
    if canonical.get("catalogue_item") is None:
        canonical.pop("catalogue_item", None)
    unsupported = unsupported_capability(body.question)
    with database.session() as db, db.begin():
        # Serialize a member's quota across all owned sessions before creating a claim.
        db.scalar(select(StudentProfile).where(StudentProfile.id == student_id).with_for_update())
        existing = db.scalar(select(StoredRequest.id).where(
            StoredRequest.student_id == student_id, StoredRequest.session_id == session_id,
            StoredRequest.idempotency_key == key))
        if existing is None and daily_limit is not None:
            start = quota_day_start()
            count = db.scalar(select(func.count()).select_from(StoredRequest).where(
                StoredRequest.student_id == student_id,
                StoredRequest.created_at >= start, StoredRequest.created_at < start + timedelta(days=1))) or 0
            if count >= daily_limit:
                raise HTTPException(429, "daily_limit_reached")
        claimed = claim(db, student_id, session_id, key, canonical)
        if claimed.status in ("completed", "failed"):
            # Follow-up catalogue choices are internal persistence metadata, not
            # changes to the public answer returned by exact-key replay.
            return {name: value for name, value in (claimed.result or {}).items() if name != "simulation_source"}
        if unsupported:
            outcome = finish_unsupported(db, claimed.request_id, claimed.token,
                                         unsupported.code, unsupported.message)
            return UnsupportedOutcome.model_validate(outcome).model_dump(mode="json")
        if not getattr(gateway, "available", True):
            raise HTTPException(503, "provider_unavailable")
        context, prompt, max_words = _prepared(db, student_id, session_id, body)
        if body.catalogue_item is not None:
            reference = body.catalogue_item
            listing = catalogue_detail(db, reference.kind, reference.id, reference.version)
            prompt = with_listing(prompt, listing)
    started = perf_counter()
    try:
        messages = prompt.messages
        if context is not None:
            messages = [{"role": "system", "content": INSTRUCTION}, *messages]
        preview = ""
        def checked_delta(value):
            nonlocal preview
            preview += value
            public, _ = split_intent(preview)
            if has_forbidden_authority_claim(public) or any(ord(char) < 32 and char not in "\n\t" for char in public):
                raise GatewayError("invalid_provider_output")
            on_delta(value)
        generated = gateway.generate_stream(messages, checked_delta) if on_delta is not None and hasattr(gateway, "generate_stream") else gateway.generate(messages)
        answer_text, need = split_intent(generated.text)
        generated = replace(generated, text=answer_text)
        result = _answer(claimed.request_id, context, generated, max_words=max_words, rendering_decision=prompt.rendering_decision)
        if prompt.rendering_decision is not None:
            result["rendering_decision"] = {key: prompt.rendering_decision[key] for key in ("mode", "preferred_template", "reason")}
            selected = [block["template"] for block in result["blocks"] if block["kind"] == "math_visual"]
            result["rendering_decision"].update(selected_templates=selected,
                selected_engines=[TEMPLATES[name]["engine"] for name in selected])
        if prompt.visual_routing is not None:
            result["visual_routing"] = prompt.visual_routing
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
            if body.catalogue_item is not None:
                reference = body.catalogue_item
                catalogue_detail(db, reference.kind, reference.id, reference.version)
            saved = finalize(db, claimed.request_id, claimed.token, body.question, result,
                resolved=context, prompt_version=prompt.version + ("-intent1" if context else ""),
                profile_version=prompt.profile_version, model=generated.model,
                input_tokens=generated.input_tokens, output_tokens=generated.output_tokens,
                latency_ms=round((perf_counter() - started) * 1000))
        if prompt.visual_routing and prompt.visual_routing["simulation_engine"] is not None:
            transient.arm(student_id, saved["message_id"], response_language=body.response_language)
        return saved
    except HTTPException as exc:
        if exc.detail in ("unavailable_context", "catalogue_item_unavailable"):
            with database.session() as db, db.begin():
                fail(db, claimed.request_id, claimed.token, exc.detail)
        raise
