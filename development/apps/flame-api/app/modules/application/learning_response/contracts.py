from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class RecommendationPart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed", "none", "pending", "unavailable"]
    data: dict | None = None
    code: str | None = None


class AnswerPart(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["completed", "unsupported", "unavailable"]
    blocks: list[dict] = Field(default_factory=list)


class LearningResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1] = 1
    message_id: UUID | None = None
    request_id: UUID | None = None
    answer: AnswerPart | None = None
    recommendations: RecommendationPart
