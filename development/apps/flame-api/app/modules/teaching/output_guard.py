"""Reject obvious fabricated authority in direct, ungrounded model text.

These checks are narrow. Educator review still determines factual and age suitability.
"""
import re

_FORBIDDEN = (
    re.compile(r"https?://|\bwww\.", re.I),
    re.compile(r"\b(?:according to|as stated in|quoted from)\s+(?:your|the|an?)\s+(?:uploaded\s+|attached\s+)?(?:textbook|file|pdf|video|audio)\b", re.I),
    re.compile(r"\bI\s+(?:read|reviewed|checked|verified|watched|listened to)\s+(?:your|the|an?)\s+(?:uploaded\s+|attached\s+)?(?:textbook|file|pdf|video|audio)\b", re.I),
    re.compile(r"\b(?:your\s+(?:official|final)\s+(?:grade|score)\s+is|here\s+is\s+the\s+official\s+answer)\b", re.I),
)


def has_forbidden_authority_claim(text: str) -> bool:
    return any(pattern.search(text) for pattern in _FORBIDDEN)
