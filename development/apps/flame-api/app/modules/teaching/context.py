"""Authoritative, published teaching paths. Names are data, never authority."""
from dataclasses import dataclass
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.modules.curriculum.catalogue import subject_path
from app.modules.curriculum.models import Category, Curriculum, Domain, Level, Subject, Subtopic, Topic


@dataclass(frozen=True)
class TeachingContext:
    ids: dict[str, UUID | None]
    names: dict[str, str | None]
    revision: int
    curriculum_description: str | None
    learning_outcome: str | None


def load_context(db, ids: dict[str, UUID | None], *, expected_revision: int | None = None) -> TeachingContext:
    """Recheck every ancestor and publication before using optional teaching metadata."""
    try:
        subject_path(db, **ids)
    except HTTPException as exc:
        if expected_revision is not None:
            raise HTTPException(409, "unavailable_context") from exc
        raise
    curriculum = db.get(Curriculum, ids["curriculum_id"])
    if expected_revision is not None and curriculum.revision != expected_revision:
        raise HTTPException(409, "unavailable_context")
    classes = (Curriculum, Level, Subject, Domain, Category, Topic, Subtopic)
    keys = ("curriculum", "level", "subject", "domain", "category", "topic", "subtopic")
    names = {key: db.get(cls, ids[key + "_id"]).name if ids.get(key + "_id") else None
             for key, cls in zip(keys, classes)}
    topic = db.get(Topic, ids["topic_id"])
    return TeachingContext(ids=ids, names=names, revision=curriculum.revision,
                           curriculum_description=curriculum.description or None,
                           learning_outcome=topic.learning_outcome or None)


def published_paths(db, *, limit: int = 10000) -> list[TeachingContext]:
    """Candidate list for conservative Curiosity matching; never includes archived branches."""
    rows = db.execute(select(Curriculum.id, Level.id, Subject.id, Domain.id, Category.id,
                             Topic.id, Subtopic.id)
        .join(Level, Level.curriculum_id == Curriculum.id)
        .join(Subject, Subject.level_id == Level.id)
        .join(Domain, Domain.subject_id == Subject.id)
        .join(Topic, Topic.domain_id == Domain.id)
        .outerjoin(Category, Category.id == Topic.category_id)
        .join(Subtopic, Subtopic.topic_id == Topic.id)
        .where(Curriculum.state == "published", Level.archived.is_(False),
               Subject.archived.is_(False), Domain.archived.is_(False),
               Topic.archived.is_(False), Subtopic.archived.is_(False),
               (Topic.category_id.is_(None)) | (Category.archived.is_(False)))
        .limit(limit + 1)).all()
    if len(rows) > limit:
        raise HTTPException(503, "catalogue_resolution_limit")
    keys = ("curriculum_id", "level_id", "subject_id", "domain_id", "category_id",
            "topic_id", "subtopic_id")
    return [load_context(db, dict(zip(keys, row))) for row in rows]
