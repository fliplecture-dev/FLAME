"""Structured decisions validated before storing a new selection; legacy JSON stays readable."""
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.contracts.catalogue import CandidateKind, Availability


class Choice(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: UUID
    candidate_kind: CandidateKind
    candidate_type: str
    version: int = Field(ge=1)
    display_mode: Literal["inline", "optional card", "reference earlier"]
    reason: str = Field(min_length=1, max_length=2000)
    availability_state: Availability
    reference_message_id: UUID | None = None
    displayed: bool = False
    failed: bool | None = None


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[2]
    learning_intent: Literal["explain", "demonstrate", "practise", "human_help", "follow_up"]
    concept: str = Field(max_length=100)
    intent_source: Literal["llm", "fallback"]
    language: str | None
    primary: Choice | None
    alternative: Choice | None
    display_mode: Literal["inline", "optional card", "reference earlier", "none"]
