"""Versioned teaching-depth rules. A level label is interpreted only when explicit."""
from dataclasses import dataclass
import re

PROFILE_VERSION = "kg5-1"


@dataclass(frozen=True)
class TeachingProfile:
    version: str
    level: int | None
    max_words: int
    instruction: str


def _explicit_level(value: str | None) -> int | None:
    if not value:
        return None
    normalized = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    if normalized in {"kg", "grade kg", "class kg", "kindergarten", "k g", "stem foundation kg"}:
        return 0
    match = re.fullmatch(r"(?:stem foundation )?(?:level |grade |class )?([1-5])", normalized)
    if match:
        return int(match.group(1))
    roman = re.fullmatch(r"(?:stem foundation )?level (i|ii|iii|iv|v)", normalized)
    if roman:
        return {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5}[roman.group(1)]
    return None


def level_number(code: str | None, name: str | None) -> int | None:
    values = {number for number in (_explicit_level(code), _explicit_level(name))
              if number is not None}
    return values.pop() if len(values) == 1 else None


def profile(code: str | None, name: str | None, *, curiosity: bool = False) -> TeachingProfile:
    number = level_number(code, name)
    if number is None:
        return TeachingProfile(PROFILE_VERSION, None, 100,
            "Use plain language suitable for learners under 15. Ask one clarifying question if the learner's level matters. Avoid expert depth.")
    limits = (60, 75, 90, 110, 130, 150)
    instruction = (
        "Use short familiar words and concrete everyday examples. "
        "Explain one idea at a time. Define any necessary new word. "
        "For mathematics, show small steps and check units; avoid unexplained symbols. "
        "Do not assume prior knowledge above this level."
    )
    if number == 0:
        instruction += " Use counting or observation before equations."
    if curiosity:
        instruction += " Keep every response suitable for learners under 15."
    return TeachingProfile(PROFILE_VERSION, number, limits[number], instruction)

