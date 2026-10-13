"""Additive envelopes. Never run recommendations on the answer's critical path."""
import logging
from fastapi import HTTPException
from app.modules.learning_response.contracts import LearningResponse, RecommendationPart, AnswerPart

LOGGER = logging.getLogger("flame.learning_response")


def compose_answer(answer, *, mode):
    if answer.get("status") == "error":
        return answer  # Existing error response/status remains authoritative.
    completed = answer.get("status") == "ok" and bool(answer.get("message_id"))
    envelope = LearningResponse(message_id=answer.get("message_id"), request_id=answer.get("request_id"),
        answer=AnswerPart(status="completed" if completed else "unsupported", blocks=answer.get("blocks", [])),
        recommendations=RecommendationPart(status="pending" if completed and mode == "study" else "none"))
    return {**answer, "learning_response": envelope.model_dump(mode="json")}


def compose_recommendations(message_id, load):
    try:
        result = load()
    except HTTPException:
        raise  # Ownership/context/version failures never become successful anonymous results.
    except Exception as error:
        code = "recommendation_timeout" if isinstance(error, TimeoutError) else "recommendation_unavailable"
        LOGGER.warning("recommendation_composition_failed", extra={"fields": {
            "message_id": str(message_id), "exception_type": type(error).__name__, "code": code}})
        result = {"status": "unavailable", "resources": [], "teachers": [], "kits": []}
        part = RecommendationPart(status="unavailable", code=code)
    else:
        has_choices = bool(result.get("resources") or result.get("teachers") or result.get("kits"))
        part = RecommendationPart(status="completed" if has_choices else "none", data=result)
    envelope = LearningResponse(message_id=message_id, recommendations=part)
    return {**result, "learning_response": envelope.model_dump(mode="json")}
