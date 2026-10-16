"""B6 boundary between owned sessions and the future B7 provider adapter."""
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException

from app.modules.functional.conversations.router import bounded_history, owned
from app.modules.functional.curriculum.models import Level
from app.contracts.decisions import TeachingContext
from app.modules.functional.curriculum.teaching_context import load_context, published_paths
from app.modules.application.teaching.clarification import cancel_pending
from app.modules.decision_engine.teaching.profiles import profile
from app.modules.application.teaching.prompt import Prompt, assemble
from app.modules.decision_engine.teaching.resolution import resolve


@dataclass(frozen=True)
class Preparation:
    status: str
    prompt: Prompt | None
    context: TeachingContext | None
    candidates: tuple[TeachingContext, ...] = ()


def prepare(db, student_id: UUID, session_id: UUID, question: str) -> Preparation:
    """Return a prompt only for one current validated school path."""
    session = owned(db, student_id, session_id)
    if session.mode == "study":
        ids = {key: UUID(value) if value else None
               for key, value in session.context_snapshot.items() if key.endswith("_id")}
        context = load_context(db, ids, expected_revision=session.revision)
    else:
        cancel_pending(db, student_id, session_id)
        resolution = resolve(question, published_paths(db))
        if resolution.status != "resolved":
            return Preparation(resolution.status, None, None, resolution.candidates)
        context = resolution.context
    level = db.get(Level, context.ids["level_id"])
    teaching = profile(level.code, level.name, curiosity=session.mode == "curiosity")
    history = bounded_history(db, student_id, session_id)
    return Preparation("ready", assemble(question, context, teaching, history,
                       curiosity=session.mode == "curiosity"), context)



