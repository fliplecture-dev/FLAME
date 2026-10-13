"""Catalogue services exchange validated data, never ORM entities or storage keys."""
import re
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

CandidateKind = Literal["resource", "tutor", "kit"]
Availability = Literal["available", "unavailable", "unknown", "unconfirmed"]


def availability(raw: str | None) -> Availability:
    if not raw or str(raw).strip().casefold() in {"unknown", "not specified", "tbd"}:
        return "unknown"
    if re.search(r"unavailable|not available|out of stock|closed|on leave|fully booked", raw, re.I):
        return "unavailable"
    if raw.strip().casefold() in {"available", "in stock", "ready", "online"}:
        return "available"
    return "unconfirmed"


class CatalogueCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    id: UUID
    kind: CandidateKind
    type: str
    version: int = Field(ge=1)
    title: str = Field(min_length=1)
    description: str | None = None
    metadata: str = ""
    availability_state: Availability
    languages: list[str] = Field(default_factory=list)
    topic_expertise: bool = False
    precise_mapping: bool = False
    card: dict
    mime_type: str | None = None
    alt_text: str | None = None
    caption_or_transcript: str | None = None
    accessibility_note: str | None = None
    published: bool = True
    availability: str = "available"
    concepts: list[str] = Field(default_factory=list)
    synonyms: list[str] = Field(default_factory=list)
    grade_min: int | None = None
    grade_max: int | None = None
    purposes: list[str] = Field(default_factory=list)

    def selection_data(self) -> dict:
        return self.model_dump(mode="json", exclude={"card"})


def suitable_for(candidate: CatalogueCandidate, grade: str, language: str | None = None) -> bool:
    """Explicit suitability for catalogue browsing/delivery, independent of ranking."""
    match = re.search(r"(?:grade|class|level)\s*(\d+|kg)", grade, re.I)
    if match and candidate.grade_min is not None and candidate.grade_max is not None:
        number = 0 if match[1].lower() == "kg" else int(match[1])
        if not candidate.grade_min <= number <= candidate.grade_max:
            return False
    if language and candidate.languages:
        aliases = {"english": "en", "tamil": "ta", "hindi": "hi"}
        languages = {aliases.get(value.lower(), value.lower().split("-")[0]) for value in candidate.languages}
        if language.lower().split("-")[0] not in languages:
            return False
    return True
