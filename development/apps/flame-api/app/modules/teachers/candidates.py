"""Teacher-owned published expertise and profile eligibility."""
from app.contracts.learning_metadata import candidate_metadata
from collections import defaultdict
from sqlalchemy import select, or_
from app.contracts.catalogue import CatalogueCandidate, availability
from app.modules.teachers.models import Teacher, TeacherExpertise


def public_teacher(db, row, subject_id, topic_id, expertise=None):
    if expertise is None:
        expertise = db.scalars(select(TeacherExpertise).where(TeacherExpertise.teacher_id == row.id,
        TeacherExpertise.subject_id == subject_id,
        or_(TeacherExpertise.topic_id.is_(None), TeacherExpertise.topic_id == topic_id))).all()
    return {"id": str(row.id), "name": row.name, "bio": row.bio, "qualifications": row.qualifications,
        "experience": row.experience, "languages": row.languages, "availability": row.availability,
        "expertise": [{"subject_id": str(e.subject_id), "topic_id": str(e.topic_id) if e.topic_id else None,
                       "claim_status": e.claim_status} for e in expertise]}


def eligible_candidates(db, subject_id, topic_id):
    rows = db.scalars(select(Teacher).join(TeacherExpertise).where(Teacher.published.is_(True),
        TeacherExpertise.subject_id == subject_id,
        or_(TeacherExpertise.topic_id.is_(None), TeacherExpertise.topic_id == topic_id)).distinct()).all()
    # One batch query replaces one expertise query per tutor; request-local only.
    by_teacher = defaultdict(list)
    if rows:
        for link in db.scalars(select(TeacherExpertise).where(TeacherExpertise.teacher_id.in_([r.id for r in rows]),
                TeacherExpertise.subject_id == subject_id,
                or_(TeacherExpertise.topic_id.is_(None), TeacherExpertise.topic_id == topic_id))).all():
            by_teacher[link.teacher_id].append(link)
    result = []
    for r in rows:
        if availability(r.availability) == "unavailable":
            continue
        card = public_teacher(db, r, subject_id, topic_id, by_teacher[r.id])
        education = candidate_metadata(r.learning_metadata)
        education["languages"] = education["languages"] or r.languages
        result.append(CatalogueCandidate(**education, id=r.id, kind="tutor", type="tutor", version=r.version,
            title=r.name, description=r.bio, metadata=r.qualifications or "",
            availability_state=availability(r.availability), topic_expertise=any(e["topic_id"] for e in card["expertise"]), card=card))
    return result
