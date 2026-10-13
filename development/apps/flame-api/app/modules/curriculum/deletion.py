"""Dependency review and guarded permanent curriculum deletion."""
from __future__ import annotations

from sqlalchemy import delete, func, select

from app.modules.activity_kits.models import KitTopic
from app.modules.conversations.models import ConversationSession, Message
from app.modules.curriculum.catalogue import nodes
from app.modules.curriculum.import_models import CurriculumImport, CurriculumImportCommit, CurriculumImportSource
from app.modules.curriculum.models import Category, Curriculum, CurriculumDraft, CurriculumRevision, Domain, Level, Subject, Subtopic, Topic
from app.modules.learning.models import LearningMembership
from app.modules.resources.models import ResourceTopic
from app.modules.teachers.models import TeacherExpertise


def deletion_review(session, curriculum: Curriculum) -> dict:
    groups = nodes(session, curriculum.id, include_archived=True)
    levels, subjects, domains, categories, topics, subtopics = groups
    level_ids = [item.id for item in levels]
    subject_ids = [item.id for item in subjects]
    topic_ids = [item.id for item in topics]

    def count(query):
        return int(session.scalar(query) or 0)

    resources = count(select(func.count(func.distinct(ResourceTopic.resource_id)))
                      .where(ResourceTopic.topic_id.in_(topic_ids))) if topic_ids else 0
    kits = count(select(func.count(func.distinct(KitTopic.kit_id)))
                 .where(KitTopic.topic_id.in_(topic_ids))) if topic_ids else 0
    teachers = count(select(func.count(func.distinct(TeacherExpertise.teacher_id)))
                     .where((TeacherExpertise.subject_id.in_(subject_ids)) |
                            (TeacherExpertise.topic_id.in_(topic_ids)))) if subject_ids or topic_ids else 0
    memberships = count(select(func.count(func.distinct(LearningMembership.student_id)))
                        .where(LearningMembership.curriculum_id == curriculum.id))
    sessions = count(select(func.count()).select_from(ConversationSession)
                     .where(ConversationSession.curriculum_id == curriculum.id))
    messages = count(select(func.count()).select_from(Message)
                     .where(Message.resolved_curriculum_id == curriculum.id))
    imports = count(select(func.count()).select_from(CurriculumImport)
                    .where(CurriculumImport.curriculum_id == curriculum.id))
    published = count(select(func.count()).select_from(CurriculumRevision)
                      .where(CurriculumRevision.curriculum_id == curriculum.id,
                             CurriculumRevision.change_kind == "publish"))
    revisions = count(select(func.count()).select_from(CurriculumRevision)
                      .where(CurriculumRevision.curriculum_id == curriculum.id))
    counts = {
        "hierarchy_nodes": sum(len(group) for group in groups),
        "published_revisions": published,
        "revision_history": revisions,
        "linked_resources": resources,
        "activity_kits": kits,
        "student_associations": memberships,
        "teacher_associations": teachers,
        "learning_sessions": sessions,
        "learning_messages": messages,
        "import_history": imports,
    }
    blockers = {key: value for key, value in counts.items()
                if key in ("linked_resources", "activity_kits", "student_associations",
                           "teacher_associations", "learning_sessions", "learning_messages") and value}
    return {"curriculum_id": str(curriculum.id), "name": curriculum.name, "code": curriculum.code,
            "state": curriculum.state, "version": curriculum.version, "revision": curriculum.revision,
            "counts": counts, "blockers": blockers, "can_delete": not blockers}


def delete_curriculum_records(session, curriculum: Curriculum) -> None:
    levels, subjects, domains, categories, topics, subtopics = nodes(
        session, curriculum.id, include_archived=True)
    level_ids = [item.id for item in levels]
    subject_ids = [item.id for item in subjects]
    domain_ids = [item.id for item in domains]
    category_ids = [item.id for item in categories]
    topic_ids = [item.id for item in topics]
    subtopic_ids = [item.id for item in subtopics]
    import_ids = session.scalars(select(CurriculumImport.id).where(
        CurriculumImport.curriculum_id == curriculum.id)).all()
    session.execute(delete(CurriculumImportSource).where(
        CurriculumImportSource.curriculum_id == curriculum.id))
    if import_ids:
        session.execute(delete(CurriculumImportCommit).where(
            CurriculumImportCommit.import_id.in_(import_ids)))
        session.execute(delete(CurriculumImport).where(CurriculumImport.id.in_(import_ids)))
    session.execute(delete(CurriculumDraft).where(CurriculumDraft.curriculum_id == curriculum.id))
    session.execute(delete(CurriculumRevision).where(
        CurriculumRevision.curriculum_id == curriculum.id))
    for cls, ids in ((Subtopic, subtopic_ids), (Topic, topic_ids), (Category, category_ids),
                     (Domain, domain_ids), (Subject, subject_ids), (Level, level_ids)):
        if ids:
            session.execute(delete(cls).where(cls.id.in_(ids)))
    session.delete(curriculum)
    session.flush()


