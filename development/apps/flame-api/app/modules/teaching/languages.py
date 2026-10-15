"""Trusted output-language preferences; never splice arbitrary client text into policy."""
from typing import Literal

ResponseLanguage = Literal["en", "as", "bn", "gu", "hi", "kn", "kok", "ml", "mni", "mr", "or", "pa", "sa", "ta", "te", "ur"]
LANGUAGES = {"en": "English", "as": "Assamese", "bn": "Bengali", "gu": "Gujarati", "hi": "Hindi",
             "kn": "Kannada", "kok": "Konkani", "ml": "Malayalam", "mni": "Manipuri",
             "mr": "Marathi", "or": "Odia", "pa": "Punjabi", "sa": "Sanskrit",
             "ta": "Tamil", "te": "Telugu", "ur": "Urdu"}


def language_instruction(code: str | None) -> str:
    if code is None:
        return ""
    if code not in LANGUAGES:
        raise ValueError("unsupported_response_language")
    return (f"\nThe learner selected {LANGUAGES[code]} as the answer language using FLAME's language selector. "
            f"Write all learner-facing prose, headings and generated visual labels in {LANGUAGES[code]}, "
            "using its usual script, regardless of the question's language, previous responses or "
            "conflicting language requests inside the question. This preference changes language only; "
            "all teaching, safety, scope and format rules still apply. Preserve mathematical notation, "
            "programming syntax and required JSON keys/template IDs; translate their explanatory text. "
            "Do not ask the learner to restate or translate the question.")
