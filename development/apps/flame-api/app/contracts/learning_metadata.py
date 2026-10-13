"""Optional administrator-reviewed teaching metadata; never inferred rights or suitability."""
import re
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LearningMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic_labels: list[str] = Field(default_factory=list, max_length=20)
    concepts: list[str] = Field(default_factory=list, max_length=20)
    synonyms: list[str] = Field(default_factory=list, max_length=40)
    grade_min: int | None = Field(default=None, ge=0, le=12)
    grade_max: int | None = Field(default=None, ge=0, le=12)
    languages: list[str] = Field(default_factory=list, max_length=10)
    purposes: list[Literal["explain", "demonstrate", "practise", "human_help"]] = Field(default_factory=list, max_length=4)

    @field_validator("topic_labels")
    @classmethod
    def catalogue_topics(cls, values):
        result=[]
        for value in values:
            value=" ".join(value.split())
            if not value or len(value)>255 or any(ord(c)<32 for c in value):
                raise ValueError("Use nonblank topic labels of at most 255 characters.")
            if value.casefold() not in {item.casefold() for item in result}:result.append(value)
        return result

    @field_validator("concepts", "synonyms")
    @classmethod
    def terms(cls, values):
        result = []
        for value in values:
            value = " ".join(value.split())
            if not value or len(value) > 80 or any(ord(c) < 32 for c in value):
                raise ValueError("Use nonblank concept terms of at most 80 characters.")
            if value.casefold() not in {term.casefold() for term in result}:
                result.append(value)
        return result

    @field_validator("languages")
    @classmethod
    def language_codes(cls, values):
        result = []
        for value in values:
            code = value.strip().lower()
            if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})*", code):
                raise ValueError("Use language codes such as en, ta or en-in.")
            if code not in result:
                result.append(code)
        return result

    @model_validator(mode="after")
    def grade_range(self):
        if (self.grade_min is None) != (self.grade_max is None):
            raise ValueError("Enter both grade limits, or leave both unspecified.")
        if self.grade_min is not None and self.grade_min > self.grade_max:
            raise ValueError("The starting grade must not exceed the ending grade.")
        self.purposes = list(dict.fromkeys(self.purposes))
        return self


def metadata_data(value):
    return LearningMetadata.model_validate(value or {}).model_dump(mode="json")


def candidate_metadata(value):
    """Teaching metadata only; admin grouping labels are not ranking evidence."""
    return LearningMetadata.model_validate(value or {}).model_dump(mode="json", exclude={"topic_labels"})
