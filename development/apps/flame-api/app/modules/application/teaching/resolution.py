"""Compatibility exports; policy implementation belongs to decision_engine."""
from app.modules.decision_engine.teaching.resolution import Resolution, words, contains_phrase, resolve, candidate_by_id

__all__ = ['Resolution', 'words', 'contains_phrase', 'resolve', 'candidate_by_id']
