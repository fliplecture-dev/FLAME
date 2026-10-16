"""Explicit, idempotent ORM registration shared by the app and Alembic.

Register declarations only; never open database connections or load application code.
"""
from importlib import import_module

MODEL_MODULES = (
    "app.modules.functional.bulk_transfer.models",
    "app.modules.functional.curriculum.models",
    "app.modules.functional.curriculum.import_models",
    "app.modules.functional.identity.models",
    "app.modules.functional.learning.models",
    "app.modules.functional.conversations.models",
    "app.modules.functional.conversations.topic_checks",
    "app.modules.functional.student_activity.models",
    "app.modules.functional.data_lifecycle.models",
    "app.modules.functional.recommendation_history.models",
    "app.modules.functional.resources.models",
    "app.modules.functional.teachers.models",
    "app.modules.functional.activity_kits.models",
)


def register_models() -> None:
    """Repeated calls reuse canonical Python modules and table objects."""
    for module in MODEL_MODULES:
        import_module(module)
