"""Composer entry point reuses teaching's quota, provider, idempotency and persistence."""
from app.modules.application.teaching.answer_service import ask as teaching_ask
from app.modules.application.learning_response.composer import compose_answer


def ask(database, gateway, student_id, session_id, key, body, *, daily_limit=25, on_delta=None):
    options = {"daily_limit": daily_limit}
    if on_delta is not None:
        options["on_delta"] = on_delta
    answer = teaching_ask(database, gateway, student_id, session_id, key, body, **options)
    return compose_answer(answer, mode=body.mode)
