"""Policy data contracts shared by functional services and the pure decision engine.

TypedDicts describe existing JSON shapes without coercing legacy dictionary inputs.
Choice/Decision validate new persisted selections at the application boundary.
"""
from dataclasses import dataclass
from typing import Literal, NotRequired, Protocol, Required, TypedDict
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from app.contracts.catalogue import Availability, CandidateKind

LearningIntent = Literal["explain", "demonstrate", "practise", "human_help", "follow_up"]
IntentSource = Literal["llm", "fallback"]
DisplayMode = Literal["inline", "optional card", "reference earlier", "none"]
SimulationEngine = Literal["matter", "three", "r3f", "phaser", "rive", "html5"]


@dataclass(frozen=True)
class TeachingContext:
    ids: dict[str, UUID | None]
    names: dict[str, str | None]
    revision: int
    curriculum_description: str | None
    learning_outcome: str | None


@dataclass(frozen=True)
class TeachingProfile:
    version: str
    level: int | None
    max_words: int
    instruction: str


@dataclass(frozen=True)
class Resolution:
    status: Literal["resolved", "clarification", "out_of_scope"]
    context: TeachingContext | None
    candidates: tuple[TeachingContext, ...]


@dataclass(frozen=True)
class Unsupported:
    code: str
    message: str


class InferredNeed(TypedDict):
    intent: LearningIntent
    concept: str
    language: str


class LearningNeed(InferredNeed):
    source: IntentSource


class SelectionCandidate(TypedDict, total=False):
    id: Required[str]
    kind: Required[CandidateKind]
    type: Required[str]
    version: Required[int]
    title: Required[str]
    availability_state: Required[Availability]
    description: str | None
    metadata: str
    concepts: list[str]
    synonyms: list[str]
    languages: list[str]
    purposes: list[str]
    grade_min: int | None
    grade_max: int | None
    topic_expertise: bool


class DisplayHistory(TypedDict, total=False):
    candidate_id: str
    version: int
    resource_id: str
    resource_version: int
    message_id: str
    display_mode: DisplayMode
    displayed: bool
    failed: bool


class SelectedChoice(TypedDict):
    candidate_id: str
    candidate_kind: CandidateKind
    candidate_type: str
    version: int
    display_mode: Literal["inline", "optional card", "reference earlier"]
    reason: str
    availability_state: Availability
    reference_message_id: str | None
    displayed: bool
    failed: NotRequired[bool]


class RecommendationDecision(TypedDict):
    schema_version: Literal[2]
    learning_intent: LearningIntent
    concept: str
    intent_source: IntentSource
    language: str | None
    primary: SelectedChoice | None
    alternative: SelectedChoice | None
    display_mode: DisplayMode


class ImageDecision(TypedDict):
    schema_version: Literal[1]
    resource_id: str | None
    resource_version: int | None
    display_mode: Literal["inline", "reference earlier", "none"]
    reason: str
    displayed: bool
    reference_message_id: str | None


class ImageCandidate(Protocol):
    """Read-only structural view accepted from DTOs and legacy image fixtures."""
    id: UUID | str
    type: str
    title: str
    description: str | None
    alt_text: str | None
    caption_or_transcript: str | None
    accessibility_note: str | None
    published: bool
    availability: str
    version: int


class VisualHistoryTurn(TypedDict, total=False):
    user: list[dict]
    assistant: list[dict]


class RenderingDecision(TypedDict):
    mode: Literal["auto", "text", "chart", "math"]
    preferred_template: str | None
    allowed_templates: list[str]
    reason: str
    max_activities: NotRequired[int]
    allow_charts: NotRequired[bool]
    require_graph: NotRequired[bool]
    fallback_graph: NotRequired[dict]


class VisualRoutingDecision(TypedDict):
    policy_version: str
    response_kind: Literal["text", "math", "simulation"]
    visual_requested: bool
    simulation_engine: SimulationEngine | None
    media_first: bool
    allow_media_recommendations: bool
    rendering: RenderingDecision
    reason: str
    response_language: NotRequired[str | None]
    simulation_question: NotRequired[str]


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
    learning_intent: LearningIntent
    concept: str = Field(max_length=100)
    intent_source: IntentSource
    language: str | None
    primary: Choice | None
    alternative: Choice | None
    display_mode: DisplayMode
