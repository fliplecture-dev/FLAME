"""Shared positive/negative visual vocabulary; never infer intent from context alone."""
import re

VISUAL_WORDS = r"(?:show(?:me)?|simulat\w*|visuali[sz]\w*|visuals?|interactiv\w*|creat(?:e[ds]?|ing)|animat\w*|dragg\w*|rotat\w*|render\w*|build|draw|display|make|graphs?|plott?\w*|demonstrat\w*)"


def normalized(question: str) -> str:
    return re.sub(r"\s+", " ", question.casefold().replace("’", "'")).strip()


def text_requested(question: str) -> bool:
    q = normalized(question)
    return bool(re.search(
        r"\b(?:text[ -]only|just text|only text)\b|"
        r"\b(?:no|without|skip|avoid)\s+(?:any\s+|the\s+|an?\s+)?(?:visual\w*|simulat\w*|animat\w*|interactiv\w*|diagrams?|graphs?|charts?|activities)\b|"
        r"\b(?:do not|don't|dont|never)\s+(?:show(?:\s+me)?|simulat\w*|visuali[sz]\w*|creat\w*|animat\w*|render\w*|display|draw|graph\w*|plot\w*)\b", q))


def visual_requested(question: str) -> bool:
    return not text_requested(question) and bool(re.search(r"\b" + VISUAL_WORDS + r"\b", normalized(question)))
