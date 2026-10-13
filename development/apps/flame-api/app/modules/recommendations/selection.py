"""Small deterministic ranker; catalogue eligibility belongs to retrieval, not the model."""
import re
from app.contracts.catalogue import availability
from app.modules.recommendations.image_selection import tokens

GENERIC = set("test testing understanding practise practice quiz tutor teacher human need help video animation process movement works understanding demonstrate demo identifying description available english tamil hindi interactive simulation simulate experiment".split())


def concepts(text):
    return tokens(text) - GENERIC


def fallback_need(question, previous=""):
    q = question.casefold()
    interactive_request = bool(re.search(r"\b(interactive|simulation|simulate|experiment)\b", q))
    intent = ("human_help" if re.search(r"\b(tutor|teacher|human|person)\b", q) and re.search(r"\b(help|need|want|find|speak|talk|tutor)\b", q)
              else "demonstrate" if interactive_request
              else "practise" if re.search(r"\b(test|quiz|practi[cs]e|activity|exercise)\b", q)
              else "demonstrate" if re.search(r"\b(video|animation|demonstrat\w*|movement)\b|show how|how .*works", q)
              else "explain" if concepts(question) else "follow_up")
    anchors = concepts(question) or concepts(previous)
    language = "ta" if re.search(r"[\u0b80-\u0bff]", question) else "und" if re.search(r"[^\x00-\x7f]", question) else "en"
    return {"intent": intent, "concept": " ".join(sorted(anchors))[:100], "language": language, "source": "fallback"}


def learning_need(question, previous, inferred=None):
    fallback = fallback_need(question, previous)
    if not inferred:
        return fallback
    # Never offer a human automatically, and never accept an invented concept.
    anchors = concepts(question) or concepts(previous)
    model_concepts = concepts(inferred.get("concept", ""))
    if not model_concepts or not model_concepts & anchors:
        return fallback
    if inferred.get("intent") == "human_help" and fallback["intent"] != "human_help":
        return fallback
    return {**inferred, "source": "llm"}


def select_recommendations(candidates, need, question, answer, *, grade="", history=(), precise_ids=()):
    anchors = concepts(need["concept"])
    interactive_request = bool(re.search(r"\b(interactive|simulation|simulate|experiment)\b", question, re.I))
    explicit = interactive_request or bool(re.search(r"\b(show|repeat|display|view)\b.*\b(again|image|picture|diagram|video|animation|resource)\b", question, re.I))
    intent = need["intent"]
    answer_concepts = concepts(answer)
    ranked = []
    grade_match = re.search(r"(?:grade|class|level)\s*(\d+|kg)", grade, re.I)
    for c in candidates:
        if c["availability_state"] == "unavailable":
            continue
        kind, media_type = c["kind"], c["type"]
        if kind == "tutor" and intent != "human_help" or kind == "kit" and intent != "practise":
            continue
        if intent == "human_help" and kind != "tutor":
            continue
        structured = " ".join(c.get("concepts", []) + c.get("synonyms", []))
        text = " ".join(filter(None, [c["title"], c.get("description"), c.get("metadata"), structured]))
        if intent == "practise" and kind != "kit" and "practise" not in c.get("purposes", []) and not re.search(r"quiz|practi[cs]e|exercise|worksheet", text, re.I):
            continue
        if intent == "demonstrate" and media_type not in {"animation", "video", "external_video"} and not (media_type == "interactive" and interactive_request) and "demonstrate" not in c.get("purposes", []) and not re.search(r"steps|process|sequence|flow|movement", text, re.I):
            continue
        if intent == "follow_up" and media_type not in {"image", "diagram"} and not explicit:
            continue
        grades = re.findall(r"(?:grade|class|level)\s*(\d+|kg)", c["title"], re.I) or re.findall(r"(?:grade|class|level)\s*(\d+|kg)", text, re.I)
        if grade_match:
            current_grade = 0 if grade_match.group(1).lower() == "kg" else int(grade_match.group(1))
            if c.get("grade_min") is not None and c.get("grade_max") is not None:
                if not c["grade_min"] <= current_grade <= c["grade_max"]:
                    continue
            elif grades and grade_match.group(1).lower() not in [g.lower() for g in grades]:
                continue
        languages = c.get("languages") or []
        lang_names = {"en": "english", "ta": "tamil", "hi": "hindi"}
        normalized_languages = {str(l).lower().split("-")[0] for l in languages}
        if languages and need.get("language") not in normalized_languages and lang_names.get(need.get("language")) not in normalized_languages:
            continue
        text_concepts = concepts(text)
        structured_concepts = concepts(structured)
        overlap = anchors & text_concepts
        # Expert subject/topic links are explicit qualifications for a requested tutor.
        if kind != "tutor" and (not overlap or len(overlap) / max(1, len(anchors)) < .5):
            continue
        if kind == "resource" and not explicit and not (overlap & answer_concepts or structured_concepts & answer_concepts):
            continue
        score = 8 * len(overlap) / max(1, len(anchors)) + 3 * len(overlap & concepts(c["title"]))
        score += 5 if (intent == "explain" and media_type in {"image", "diagram"} or intent == "demonstrate" and media_type in {"animation", "video", "external_video"} or intent == "practise" and kind == "kit") else 0
        score += 8 if media_type == "interactive" and interactive_request else 0
        score += 2 if intent in c.get("purposes", []) else 0
        score += min(2, len(overlap & concepts(" ".join(c.get("concepts", [])))))
        score += 2 if c["id"] in precise_ids else 0
        score += 1 if grades or c.get("topic_expertise") else 0
        prior = next((h for h in reversed(list(history)) if h.get("candidate_id") == c["id"] and h.get("version") == c["version"] and h.get("displayed") and h.get("display_mode") != "reference earlier"), None)
        score -= 2 if prior and not explicit else 0
        mode = "inline" if media_type in {"image", "diagram"} else "optional card"
        if prior and not explicit:
            mode = "reference earlier"
        elif not explicit and any(h.get("candidate_id") == c["id"] and h.get("version") == c["version"] and not h.get("failed") and h.get("display_mode") in {"inline", "optional card"} for h in history):
            continue
        phrase = need["concept"] or "this topic"
        reason = (f"This kit helps you practise {phrase}." if kind == "kit" else
                  f"This tutor lists expertise for your selected topic or subject." if kind == "tutor" else
                  f"This video demonstrates {phrase}." if media_type in {"video", "external_video", "animation"} else
                  f"This interactive lets you explore {phrase}." if media_type == "interactive" else
                  f"This illustration helps explain {phrase}.")
        ranked.append((score, c["id"], {"candidate_id": c["id"], "candidate_kind": kind, "candidate_type": media_type,
                      "version": c["version"], "display_mode": mode, "reason": reason,
                      "availability_state": c["availability_state"], "reference_message_id": prior.get("message_id") if mode == "reference earlier" else None, "displayed": False}))
    selected = [r[2] for r in sorted(ranked, key=lambda x: (-x[0], x[1]))]
    # One image inline; alternatives must add a different useful format.
    primary = selected[0] if selected else None
    alternative = next((s for s in selected[1:] if s["candidate_type"] != primary["candidate_type"] and s["display_mode"] != "inline"), None) if primary and (explicit or intent == "demonstrate") else None
    return {"schema_version": 2, "learning_intent": intent, "concept": need["concept"], "intent_source": need["source"],
            "language": need.get("language"), "primary": primary, "alternative": alternative, "display_mode": primary["display_mode"] if primary else "none"}
