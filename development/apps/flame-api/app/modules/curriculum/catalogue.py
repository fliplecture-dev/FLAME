"""B4 catalogue reads and publication validation."""
from collections import defaultdict
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select

from app.modules.curriculum.models import Category, Curriculum, Domain, Level, Subject, Subtopic, Topic


def fail(status: int, code: str):
    raise HTTPException(status, code)


def curriculum_or_404(session, curriculum_id: UUID, *, published: bool = True, lock: bool = False):
    query = select(Curriculum).where(Curriculum.id == curriculum_id)
    if lock:
        query = query.with_for_update()
    row = session.scalar(query)
    if row is None or row.state == "archived" or (published and row.state != "published"):
        fail(404, "curriculum_not_found")
    return row


def nodes(session, curriculum_id: UUID, *, include_archived: bool = False):
    levels = session.scalars(select(Level).where(Level.curriculum_id == curriculum_id)).all()
    subjects = session.scalars(select(Subject).where(Subject.level_id.in_([n.id for n in levels]))).all() if levels else []
    domains = session.scalars(select(Domain).where(Domain.subject_id.in_([n.id for n in subjects]))).all() if subjects else []
    categories = session.scalars(select(Category).where(Category.domain_id.in_([n.id for n in domains]))).all() if domains else []
    topics = session.scalars(select(Topic).where(Topic.domain_id.in_([n.id for n in domains]))).all() if domains else []
    subtopics = session.scalars(select(Subtopic).where(Subtopic.topic_id.in_([n.id for n in topics]))).all() if topics else []
    groups = (levels, subjects, domains, categories, topics, subtopics)
    if not include_archived:
        groups = tuple([node for node in group if not node.archived] for group in groups)
    return groups


def tree(session, curriculum: Curriculum, *, level_id: UUID | None = None, include_archived: bool = False):
    levels, subjects, domains, categories, topics, subtopics = nodes(session, curriculum.id, include_archived=include_archived)
    by_parent = [defaultdict(list) for _ in range(6)]
    for group, field, index in (
        (levels, "curriculum_id", 0), (subjects, "level_id", 1),
        (domains, "subject_id", 2), (categories, "domain_id", 3),
        (topics, "domain_id", 4), (subtopics, "topic_id", 5),
    ):
        for node in group:
            by_parent[index][getattr(node, field)].append(node)
    def ordered(items):
        return sorted(items, key=lambda n: (n.display_order, n.name.casefold(), str(n.id)))
    def common(node):
        result = {"id": str(node.id), "name": node.name, "display_order": node.display_order, "version": node.version}
        if include_archived:
            result["archived"] = node.archived
        return result
    def topic_data(topic):
        return {**common(topic), "learning_outcome": topic.learning_outcome,
                "subtopics": [common(st) for st in ordered(by_parent[5][topic.id])]}
    def domain_data(domain):
        return {**common(domain),
                "topics": [topic_data(t) for t in ordered(by_parent[4][domain.id]) if t.category_id is None],
                "categories": [{**common(c), "topics": [topic_data(t) for t in ordered(by_parent[4][domain.id]) if t.category_id == c.id]}
                               for c in ordered(by_parent[3][domain.id])]}
    data = {"id": str(curriculum.id), "code": curriculum.code, "name": curriculum.name,
            "description": curriculum.description, "state": curriculum.state, "version": curriculum.version,
            "revision": curriculum.revision,
            "levels": [{**common(level), "subjects": [
                {**common(subject), "domains": [domain_data(d) for d in ordered(by_parent[2][subject.id])]}
                for subject in ordered(by_parent[1][level.id])]}
                for level in ordered(by_parent[0][curriculum.id]) if level_id is None or level.id == level_id]}
    if level_id and not data["levels"]:
        fail(404, "level_not_found")
    return data


def validate_publishable(session, curriculum: Curriculum):
    levels, subjects, domains, categories, topics, subtopics = nodes(session, curriculum.id)
    if not levels or not subjects or not domains or not topics or not subtopics:
        fail(422, "incomplete_curriculum")
    level_ids = {n.id for n in levels}
    subject_ids = {n.id for n in subjects if n.level_id in level_ids}
    domain_ids = {n.id for n in domains if n.subject_id in subject_ids}
    category_ids = {n.id for n in categories if n.domain_id in domain_ids}
    valid_topics = [n for n in topics if n.domain_id in domain_ids and (n.category_id is None or n.category_id in category_ids)]
    children = {n.topic_id for n in subtopics}
    if not valid_topics or any(n.id not in children for n in valid_topics):
        fail(422, "topic_requires_subtopic")


def ancestor_curriculum(session, kind: str, node_id: UUID):
    kinds = {"level": Level, "subject": Subject, "domain": Domain, "category": Category,
             "topic": Topic, "subtopic": Subtopic}
    cls = kinds.get(kind)
    if cls is None:
        fail(404, "unknown_kind")
    node = session.get(cls, node_id)
    if node is None:
        fail(404, "node_not_found")
    current = node
    while not isinstance(current, Level):
        if current.archived:
            fail(409, "ancestor_archived")
        if isinstance(current, Subject):
            current = session.get(Level, current.level_id)
        elif isinstance(current, Domain):
            current = session.get(Subject, current.subject_id)
        elif isinstance(current, Category):
            current = session.get(Domain, current.domain_id)
        elif isinstance(current, Topic):
            current = session.get(Domain, current.domain_id)
        else:
            current = session.get(Topic, current.topic_id)
        if current is None:
            fail(404, "ancestor_not_found")
    if current.archived:
        fail(409, "ancestor_archived")
    curriculum = curriculum_or_404(session, current.curriculum_id, published=False, lock=True)
    return node, curriculum


def subject_path(session, curriculum_id: UUID, level_id: UUID | None, subject_id: UUID | None,
                 domain_id: UUID | None = None, category_id: UUID | None = None,
                 topic_id: UUID | None = None, subtopic_id: UUID | None = None):
    curriculum_or_404(session, curriculum_id)
    if subject_id is not None and level_id is None:
        fail(422, "subject_requires_level")
    if domain_id is not None and subject_id is None:
        fail(422, "domain_requires_subject")
    if category_id is not None and domain_id is None:
        fail(422, "category_requires_domain")
    if topic_id is not None and domain_id is None:
        fail(422, "topic_requires_domain")
    if subtopic_id is not None and topic_id is None:
        fail(422, "subtopic_requires_topic")
    if level_id is None:
        return
    level = session.get(Level, level_id)
    if level is None or level.archived or level.curriculum_id != curriculum_id:
        fail(422, "invalid_level_path")
    if subject_id is None:
        return
    subject = session.get(Subject, subject_id)
    if subject is None or subject.archived or subject.level_id != level_id:
        fail(422, "invalid_subject_path")
    if domain_id is None:
        return
    domain = session.get(Domain, domain_id)
    if domain is None or domain.archived or domain.subject_id != subject_id:
        fail(422, "invalid_domain_path")
    if category_id is not None:
        category = session.get(Category, category_id)
        if category is None or category.archived or category.domain_id != domain_id:
            fail(422, "invalid_category_path")
    if topic_id is None:
        return
    topic = session.get(Topic, topic_id)
    if topic is None or topic.archived or topic.domain_id != domain_id or topic.category_id != category_id:
        fail(422, "invalid_topic_path")
    if subtopic_id is not None:
        subtopic = session.get(Subtopic, subtopic_id)
        if subtopic is None or subtopic.archived or subtopic.topic_id != topic_id:
            fail(422, "invalid_subtopic_path")
