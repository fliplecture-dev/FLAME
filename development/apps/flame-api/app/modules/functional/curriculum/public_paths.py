"""Validated curriculum ancestry interface for catalogue consumers."""
from uuid import UUID
from app.core.domain_errors import fail
from app.modules.functional.curriculum.catalogue import ancestor_curriculum
from app.modules.functional.curriculum.models import Domain, Subject, Level, Topic, Subtopic


def path_info(session, topic_id: UUID, subtopic_id: UUID | None = None, *, published: bool = False):
    topic, curriculum = ancestor_curriculum(session, "topic", topic_id)
    if subtopic_id:
        subtopic = session.get(Subtopic, subtopic_id)
        if subtopic is None or subtopic.archived or subtopic.topic_id != topic.id:
            fail(422, "invalid_resource_path")
    domain = session.get(Domain, topic.domain_id)
    subject = session.get(Subject, domain.subject_id)
    level = session.get(Level, subject.level_id)
    if published and curriculum.state != "published":
        fail(404, "resource_path_unavailable")
    return {"curriculum_id": curriculum.id, "curriculum_revision": curriculum.revision,
            "level_id": level.id, "subject_id": subject.id, "topic_id": topic.id,
            "subtopic_id": subtopic_id}



def describe_path(db, topic_id, subtopic_id, *, published=True):
    result = path_info(db, topic_id, subtopic_id, published=published)
    level = db.get(Level, result["level_id"])
    topic = db.get(Topic, topic_id)
    leaf = db.get(Subtopic, subtopic_id) if subtopic_id else None
    return {**result, "grade": level.name, "topic_name": topic.name,
            "subtopic_name": leaf.name if leaf else "", "objective": topic.learning_outcome or ""}


def describe_browse_path(db, topic_id, subtopic_id=None):
    """One read-only query for member browsing; do not lock an editable curriculum."""
    from sqlalchemy import select, and_, false
    from app.modules.functional.curriculum.models import Curriculum, Category
    row = db.execute(select(Topic, Domain, Subject, Level, Curriculum, Category, Subtopic).select_from(Topic)
        .join(Domain, Topic.domain_id == Domain.id).join(Subject, Domain.subject_id == Subject.id)
        .join(Level, Subject.level_id == Level.id).join(Curriculum, Level.curriculum_id == Curriculum.id)
        .outerjoin(Category, Topic.category_id == Category.id)
        .outerjoin(Subtopic, and_(Subtopic.topic_id == Topic.id, Subtopic.id == subtopic_id) if subtopic_id else false())
        .where(Topic.id == topic_id)).first()
    if row is None:
        fail(404, "explore_path_unavailable")
    topic, domain, subject, level, curriculum, category, leaf = row
    if (curriculum.state != "published" or any(node.archived for node in (topic, domain, subject, level))
            or topic.category_id and (category is None or category.archived or category.domain_id != domain.id)
            or subtopic_id and (leaf is None or leaf.archived)):
        fail(404, "explore_path_unavailable")
    return {"curriculum_id": curriculum.id, "curriculum_revision": curriculum.revision,
            "level_id": level.id, "subject_id": subject.id, "domain_id": domain.id,
            "topic_id": topic.id, "subtopic_id": leaf.id if leaf else None,
            "grade": level.name, "topic_name": topic.name, "subtopic_name": leaf.name if leaf else "",
            "objective": topic.learning_outcome or ""}


def browse_search_paths(db):
    """Read published names and identifiers in one query, without teaching N+1 loads."""
    from sqlalchemy import select, or_
    from app.modules.functional.curriculum.models import Curriculum, Category
    return db.execute(select(Curriculum.id.label("curriculum_id"), Curriculum.name.label("curriculum"),
        Curriculum.revision.label("curriculum_revision"), Level.id.label("level_id"), Level.name.label("level"),
        Subject.id.label("subject_id"), Subject.name.label("subject"), Domain.id.label("domain_id"),
        Domain.name.label("domain"), Topic.id.label("topic_id"), Topic.name.label("topic"),
        Subtopic.id.label("subtopic_id"), Subtopic.name.label("subtopic"))
        .select_from(Topic).join(Domain, Topic.domain_id == Domain.id)
        .join(Subject, Domain.subject_id == Subject.id).join(Level, Subject.level_id == Level.id)
        .join(Curriculum, Level.curriculum_id == Curriculum.id).outerjoin(Category, Topic.category_id == Category.id)
        .outerjoin(Subtopic, (Subtopic.topic_id == Topic.id) & Subtopic.archived.is_(False))
        .where(Curriculum.state == "published", Topic.archived.is_(False), Domain.archived.is_(False),
            Subject.archived.is_(False), Level.archived.is_(False),
            or_(Topic.category_id.is_(None), (Category.archived.is_(False)) & (Category.domain_id == Domain.id)))
        .order_by(Curriculum.name, Level.name, Topic.name, Subtopic.name)).mappings().all()
