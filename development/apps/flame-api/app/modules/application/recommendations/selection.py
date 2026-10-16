"""Compatibility exports; policy implementation belongs to decision_engine."""
from app.modules.decision_engine.recommendation.selection import GENERIC, concepts, fallback_need, learning_need, select_recommendations

__all__ = ['GENERIC', 'concepts', 'fallback_need', 'learning_need', 'select_recommendations']
