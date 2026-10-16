"""Compatibility exports; policy implementation belongs to decision_engine."""
from app.modules.decision_engine.recommendation.learning_need import INTENTS, INSTRUCTION, split_intent

__all__ = ['INTENTS', 'INSTRUCTION', 'split_intent']
