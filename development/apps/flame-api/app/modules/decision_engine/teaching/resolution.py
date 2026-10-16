"""Conservative Curiosity resolution against current published school paths."""
from app.contracts.decisions import Resolution
import re
from uuid import UUID

from app.contracts.decisions import TeachingContext


def words(value: str) -> tuple[str, ...]:
    return tuple(re.findall(r"\w+", value.casefold(), flags=re.UNICODE))


def contains_phrase(question: tuple[str, ...], label: tuple[str, ...]) -> bool:
    return bool(label) and any(question[i:i + len(label)] == label
                               for i in range(len(question) - len(label) + 1))


def resolve(question: str, paths: list[TeachingContext], *,
            preferred_level: int | None = None, max_candidates: int = 8) -> Resolution:
    """Require an explicit topic/subtopic phrase; never invent a catalogue mapping."""
    terms = words(question)
    if not terms:
        return Resolution("out_of_scope", None, ())
    matches = []
    for context in paths:
        topic = words(context.names.get("topic") or "")
        subtopic = words(context.names.get("subtopic") or "")
        if contains_phrase(terms, subtopic) or contains_phrase(terms, topic):
            matches.append(context)
    if not matches:
        return Resolution("out_of_scope", None, ())
    # An explicit subtopic phrase is more precise than a parent topic phrase.
    precise = [item for item in matches if contains_phrase(terms, words(item.names.get("subtopic") or ""))]
    if precise:
        matches = precise
    # A level preference only narrows matches when it has an unambiguous explicit mapping.
    if preferred_level is not None:
        from app.modules.decision_engine.teaching.profiles import level_number
        narrowed = [item for item in matches if level_number(None, item.names.get("level")) == preferred_level]
        if narrowed:
            matches = narrowed
    unique = {item.ids["subtopic_id"]: item for item in matches}
    ordered = tuple(sorted(unique.values(), key=lambda item: (
        item.names.get("curriculum") or "", item.names.get("level") or "",
        item.names.get("subject") or "", item.names.get("topic") or "",
        item.names.get("subtopic") or "", str(item.ids["subtopic_id"]))))
    if len(ordered) == 1:
        return Resolution("resolved", ordered[0], ())
    return Resolution("clarification", None, ordered[:max_candidates])


def candidate_by_id(candidates: tuple[TeachingContext, ...], subtopic_id: UUID) -> TeachingContext | None:
    return next((item for item in candidates if item.ids["subtopic_id"] == subtopic_id), None)
