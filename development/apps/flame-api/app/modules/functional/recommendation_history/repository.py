"""Recommendation-owned persistence. Caller owns the transaction and session lock."""
from sqlalchemy import select, delete, func, or_
from app.modules.functional.recommendation_history.models import RecommendationSet


class RecommendationRepository:
    def __init__(self, db):
        self.db = db

    def get(self, session_id, message_id):
        return self.db.scalar(select(RecommendationSet).where(RecommendationSet.session_id == session_id,
            RecommendationSet.message_id == message_id).with_for_update())

    def earlier(self, session_id, message_ids):
        if not message_ids:
            return []
        rows = self.db.scalars(select(RecommendationSet).where(RecommendationSet.session_id == session_id,
            RecommendationSet.message_id.in_(message_ids))).all()
        order = {mid: index for index, mid in enumerate(message_ids)}
        return sorted(rows, key=lambda row: order[row.message_id])

    def create(self, context, resource_ids, teacher_ids, image_decision):
        row = RecommendationSet(student_id=context.student_id, session_id=context.session_id,
            message_id=context.message_id, resource_ids=resource_ids, teacher_ids=teacher_ids, image_decision=image_decision)
        self.db.add(row)
        self.db.flush()
        return row


def resource_reference_count(db, resource_id):
    rid = str(resource_id)
    return db.scalar(select(func.count()).select_from(RecommendationSet).where(or_(
        RecommendationSet.resource_ids.contains([rid]), RecommendationSet.image_decision["resource_id"].astext == rid))) or 0


def remove_for_sessions(db, session_ids):
    if session_ids:
        db.execute(delete(RecommendationSet).where(RecommendationSet.session_id.in_(session_ids)))
