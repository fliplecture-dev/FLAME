"""Conservative capability gate for requests that explicitly need unavailable evidence or media.

This is deliberately narrow: ordinary questions about books, pictures, or grades still
reach the school-topic gate. It is not a general intent or safety classifier.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Unsupported:
    code: str
    message: str


RULES = (
    (re.compile(r"\b(?:cite|quote|show|give|find)\b.{0,50}\b(?:textbook|book)\b.{0,30}\b(?:page|source|citation|evidence)\b|\b(?:which|what)\s+page\b.{0,50}\b(?:textbook|book)\b", re.I | re.S),
     Unsupported("textbook_evidence_unavailable", "I cannot verify textbook pages or citations. I can explain a selected school topic instead.")),
    (re.compile(r"\b(?:official|certified)\s+(?:answer|answer key|score|grade|mark)\b|\b(?:grade|mark|score)\s+(?:my|this|the)\s+(?:answer|test|exam|homework)\b", re.I),
     Unsupported("official_grading_unavailable", "I cannot provide official answers or grades. I can help explain the selected topic.")),
    (re.compile(r"\b(?:read|summarize|analyse|analyze|describe|explain|translate|answer questions about)\s+(?:this|my|the|an?|attached|uploaded)\s+(?:attached\s+|uploaded\s+)?(?:file|pdf|document|photo|image|picture)\b", re.I),
     Unsupported("student_file_understanding_unavailable", "I cannot read or understand uploaded files or images. Ask a text question about a school topic instead.")),
    (re.compile(r"\b(?:watch|listen to|summarize|analyse|analyze|describe|explain|transcribe)\s+(?:this|my|the|an?|attached|uploaded)\s+(?:attached\s+|uploaded\s+)?(?:video|audio|clip|recording|voice note)\b", re.I),
     Unsupported("media_understanding_unavailable", "I cannot watch videos, listen to audio, or transcribe recordings. Ask a text question about a school topic instead.")),
    (re.compile(r"\b(?:update|change|set)\s+(?:my|the)\s+(?:mastery|progress|score|grade)\b", re.I),
     Unsupported("progress_update_unavailable", "I cannot change grades or learning progress. I can help explain a school topic.")),
)


def unsupported_capability(question: str) -> Unsupported | None:
    for pattern, result in RULES:
        if pattern.search(question):
            return result
    return None
