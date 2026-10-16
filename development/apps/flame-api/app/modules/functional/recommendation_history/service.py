"""Public recommendation-history operations; callers own transactions and locks.

Application coordination may read/update a saved selection through this interface.
Other functional owners use reference counting and cleanup, never ranking code.
"""
from app.modules.functional.recommendation_history.repository import (
    RecommendationRepository, remove_for_sessions, resource_reference_count,
)

__all__ = ["RecommendationRepository", "remove_for_sessions", "resource_reference_count"]
