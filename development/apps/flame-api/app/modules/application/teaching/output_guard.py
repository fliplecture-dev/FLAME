"""Compatibility exports; policy implementation belongs to decision_engine."""
from app.modules.decision_engine.teaching.output_guard import has_forbidden_authority_claim

__all__ = ['has_forbidden_authority_claim']
