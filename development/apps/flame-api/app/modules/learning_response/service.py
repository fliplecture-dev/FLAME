"""Composer entry point reuses teaching's quota, provider, idempotency and persistence."""
from app.modules.teaching.answer_service import ask as teaching_ask
from app.modules.learning_response.composer import compose_answer


def ask(database, gateway, student_id, session_id, key, body, *, daily_limit=100):
    answer = teaching_ask(database, gateway, student_id, session_id, key, body, daily_limit=daily_limit)
    return compose_answer(answer, mode=body.mode)
