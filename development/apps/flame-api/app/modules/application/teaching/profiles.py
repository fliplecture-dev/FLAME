"""Compatibility exports; policy implementation belongs to decision_engine."""
from app.modules.decision_engine.teaching.profiles import PROFILE_VERSION, TeachingProfile, level_number, profile

__all__ = ['PROFILE_VERSION', 'TeachingProfile', 'level_number', 'profile']
