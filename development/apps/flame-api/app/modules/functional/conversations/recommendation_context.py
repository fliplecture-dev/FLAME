"""Conversation-owned read interface for per-answer recommendation consumers."""
from dataclasses import dataclass
from uuid import UUID
from sqlalchemy import select
from app.core.domain_errors import fail
from app.modules.functional.conversations.models import ConversationSession, Message, AnswerRequest


@dataclass(frozen=True)
class AnswerContext:
    session_id: UUID
    message_id: UUID
    student_id: UUID
    mode: str
    subject_id: UUID | None
    topic_id: UUID | None
    curriculum_id: UUID | None
    revision: int | None
    subtopic_id: UUID | None
    question_blocks: list
    answer_blocks: list
    earlier_questions: list[list]
    earlier_message_ids: list[UUID]
    inferred_need: dict | None
    visual_routing: dict | None = None


def load_answer(db, student_id, session_id, message_id):
    conversation = db.scalar(select(ConversationSession).where(ConversationSession.id == session_id).with_for_update())
    if conversation is None or conversation.student_id != student_id:
        fail(404, "session_not_found")
    message = db.get(Message, message_id)
    if message is None or message.session_id != session_id or message.role != "assistant":
        fail(404, "answer_not_found")
    question = db.scalar(select(Message).where(Message.session_id == session_id,
        Message.turn_number == message.turn_number, Message.role == "user"))
    previous = db.scalars(select(Message).where(Message.session_id == session_id,
        Message.turn_number < message.turn_number, Message.role == "user").order_by(Message.turn_number.desc()).limit(6)).all()
    previous_ids = db.scalars(select(Message.id).where(Message.session_id == session_id,
        Message.turn_number < message.turn_number, Message.role == "assistant").order_by(Message.turn_number)).all()
    request = db.scalar(select(AnswerRequest).where(AnswerRequest.session_id == session_id,
        AnswerRequest.result["message_id"].astext == str(message_id)))
    subtopic = (conversation.context_snapshot or {}).get("subtopic_id")
    return AnswerContext(session_id, message_id, student_id, conversation.mode, message.resolved_subject_id,
        message.resolved_topic_id, message.resolved_curriculum_id, message.resolved_revision,
        UUID(subtopic) if subtopic else None, question.blocks if question else [], message.blocks,
        [row.blocks for row in previous], list(previous_ids), (request.result or {}).get("learning_need") if request else None,
        (request.result or {}).get("visual_routing") if request else None)
