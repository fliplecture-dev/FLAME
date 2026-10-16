"""Choose a sufficiently relevant authored simulation from eligible catalogue DTOs."""
from collections.abc import Sequence
import re

from app.contracts.catalogue import CatalogueCandidate, suitable_for
from app.modules.decision_engine.recommendation.image_selection import tokens

GENERIC = frozenset("simulation simulate interactive interactivity visual visualization visualisation showme create animation science physics grade level using matter three html canvas make build based previous last above response answer topic request".split())


def select_simulation(candidates: Sequence[CatalogueCandidate], question: str, *, topic: str = "", grade: str = "",
                      language: str | None = None) -> CatalogueCandidate | None:
    def concepts(text):
        return {word for word in tokens(text) - GENERIC if not re.fullmatch(r"(?:simulat|creat|visuali[sz]|interactiv|animat)\w*", word)}
    anchors = concepts(question) or concepts(topic)
    if not anchors:
        return None
    ranked = []
    for item in candidates:
        if (item.kind != "resource" or item.type != "interactive" or item.mime_type != "text/html"
                or not item.published or item.availability_state != "available" or not suitable_for(item, grade, language)):
            continue
        text = " ".join([item.title, item.description or "", item.metadata, *item.concepts, *item.synonyms])
        if re.search(r"\b3[- ]?d\b", question, re.I) and not re.search(r"\b3[- ]?d\b", text, re.I):
            continue
        overlap = anchors & concepts(text)
        if len(overlap) / len(anchors) < .5:
            continue
        score = 8 * len(overlap) / len(anchors) + 3 * len(overlap & concepts(item.title)) + int(item.precise_mapping)
        ranked.append((score, str(item.id), item))
    return sorted(ranked, key=lambda row: (-row[0], row[1]))[0][2] if ranked else None
