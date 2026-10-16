from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID
import math
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.modules.application.teaching.math_visuals import MathVisualBlock
from app.modules.application.teaching.languages import ResponseLanguage


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Context(Contract):
    curriculum_id: UUID
    level_id: UUID
    subject_id: UUID
    domain_id: UUID
    category_id: UUID | None = None
    topic_id: UUID
    subtopic_id: UUID | None = None


class AnswerRequest(Contract):
    # Identity, version and history are loaded server-side from the session.
    question: str = Field(min_length=1, max_length=4000)
    response_language: ResponseLanguage | None = None
    context: Context | None = None
    mode: Literal["study", "curiosity"]
    action: Literal["explain"] = "explain"
    topic_check_id: UUID | None = None

    @model_validator(mode="after")
    def validate_context(self):
        if self.mode == "study" and self.context is None:
            raise ValueError("Study requires curriculum context")
        if self.mode == "curiosity" and self.context is not None:
            raise ValueError("Curiosity does not accept Study context")
        if self.topic_check_id is not None:
            raise ValueError("Answer requests do not use topic checks")
        return self


class TextBlock(Contract):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["text"]
    text: str = Field(min_length=1, max_length=6000)

    @field_validator("text")
    @classmethod
    def safe_text(cls, value):
        if any(ord(char) < 32 and char not in "\n\t" for char in value):
            raise ValueError("Text contains control characters")
        return value


class MarkdownBlock(TextBlock):
    kind: Literal["markdown"]


class ChartSeries(Contract):
    key: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
    label: str = Field(min_length=1, max_length=100)


class ChartBlock(Contract):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["chart"]
    chartType: Literal["bar", "line", "pie"]
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)
    xKey: str = Field(pattern=r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
    xLabel: str = Field(default="", max_length=100)
    yLabel: str = Field(default="", max_length=100)
    illustrative: bool = True
    series: list[ChartSeries] = Field(min_length=1, max_length=4)
    data: list[dict[str, str | float]] = Field(min_length=1, max_length=50)

    @model_validator(mode="before")
    @classmethod
    def raw_cells(cls, value):
        # Do not coerce booleans, numeric strings or nested objects to numbers.
        if isinstance(value, dict) and isinstance(value.get("data"), list):
            for row in value["data"]:
                if not isinstance(row, dict) or any(
                    type(cell) not in (str, int, float) for cell in row.values()
                ):
                    raise ValueError("Chart cells must be strings or numbers")
        return value

    @model_validator(mode="after")
    def valid_data(self):
        keys = [item.key for item in self.series]
        forbidden = {"__proto__", "prototype", "constructor"}
        if len(set(keys)) != len(keys) or self.xKey in keys or forbidden.intersection([self.xKey, *keys]):
            raise ValueError("Chart keys must be distinct and safe")
        if self.chartType == "pie" and len(keys) != 1:
            raise ValueError("Pie charts require one series")
        for row in self.data:
            if set(row) != {self.xKey, *keys}:
                raise ValueError("Chart row keys must match axes and series")
            category = row[self.xKey]
            if isinstance(category, str):
                if not category.strip() or len(category) > 100 or re.search(r"[\x00-\x1f]", category):
                    raise ValueError("Chart categories must be bounded labels")
            elif not math.isfinite(category) or abs(category) > 1e12:
                raise ValueError("Chart categories must be finite")
            for key in keys:
                cell = row[key]
                if not isinstance(cell, float) or not math.isfinite(cell) or abs(cell) > 1e12:
                    raise ValueError("Chart values must be finite numbers")
                if self.chartType == "pie" and cell < 0:
                    raise ValueError("Pie chart values must be nonnegative")
        if self.chartType == "pie" and sum(row[keys[0]] for row in self.data) <= 0:
            raise ValueError("Pie chart total must be positive")
        return self


class HeadingBlock(Contract):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["heading"]
    text: str = Field(min_length=1, max_length=200)
    level: Literal[2, 3]


class ListBlock(Contract):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["list"]
    ordered: bool = False
    items: list[str] = Field(min_length=1, max_length=20)

    @field_validator("items")
    @classmethod
    def bounded_items(cls, items):
        if any(not item.strip() or len(item) > 500 for item in items):
            raise ValueError("List items must be nonempty and bounded")
        return items


class TableBlock(Contract):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["table"]
    caption: str = Field(min_length=1, max_length=200)
    columns: list[str] = Field(min_length=1, max_length=8)
    rows: list[list[str]] = Field(max_length=30)

    @model_validator(mode="after")
    def validate_width(self):
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("Table rows must match column count")
        if any(not value.strip() or len(value) > 500 for value in self.columns):
            raise ValueError("Table headings must be nonempty and bounded")
        if any(len(value) > 500 for row in self.rows for value in row):
            raise ValueError("Table cells must be bounded")
        return self


class CalloutBlock(Contract):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["callout"]
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=2000)


LearningBlock = Annotated[
    TextBlock | MarkdownBlock | ChartBlock | MathVisualBlock | HeadingBlock | ListBlock | TableBlock | CalloutBlock,
    Field(discriminator="kind"),
]


class DirectAnswer(Contract):
    response_id: UUID
    request_id: UUID
    status: Literal["ok"] = "ok"
    curriculum_version: str | None
    blocks: list[LearningBlock] = Field(min_length=1, max_length=30)
    route: Literal["direct_llm"] = "direct_llm"
    knowledge_source: Literal["model_generated"] = "model_generated"
    grounded: Literal[False] = False
    confidence: None = None
    citations: list[str] = Field(default_factory=list, max_length=0)
    # Resource objects are provided by the catalogue in Stage 9.
    resources: list[str] = Field(default_factory=list, max_length=0)

    @model_validator(mode="after")
    def unique_bounded_blocks(self):
        if len({block.id for block in self.blocks}) != len(self.blocks):
            raise ValueError("Block IDs must be unique")
        return self


class UnsupportedOutcome(Contract):
    status: Literal["unsupported"] = "unsupported"
    request_id: UUID
    code: Literal[
        "textbook_evidence_unavailable", "official_grading_unavailable",
        "student_file_understanding_unavailable", "media_understanding_unavailable",
        "progress_update_unavailable",
    ]
    message: str = Field(min_length=1, max_length=300)



class ClarificationCandidate(Contract):
    curriculum_id: UUID
    level_id: UUID
    subject_id: UUID
    domain_id: UUID
    category_id: UUID | None = None
    topic_id: UUID
    subtopic_id: UUID
    curriculum: str
    level: str
    subject: str
    domain: str
    topic: str
    subtopic: str
    revision: int = Field(ge=1)


class ClarificationOutcome(Contract):
    status: Literal["clarification"] = "clarification"
    request_id: UUID
    clarification_id: UUID
    question: str = Field(min_length=1, max_length=4000)
    prompt: str = "Which school topic do you mean?"
    candidates: list[ClarificationCandidate] = Field(min_length=2, max_length=8)
    expires_at: datetime


class OutOfScopeOutcome(Contract):
    status: Literal["out_of_scope"] = "out_of_scope"
    request_id: UUID
    message: str = "I can help with topics in the school catalogue. Choose a topic and ask me again."


class ClarificationContinuation(Contract):
    clarification_id: UUID
    subtopic_id: UUID | None = None
    reply: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def one_choice(self):
        if (self.subtopic_id is None) == (self.reply is None):
            raise ValueError("Choose one candidate or send one reply")
        return self

