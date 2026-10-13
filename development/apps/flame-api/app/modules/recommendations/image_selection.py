"""Conservative, deterministic visual relevance. Associations authorize, not select."""
import re

STOP = set("a an the is are was were be been it this that these those they them he she we you i my your our their to of for in on at by with from and or as do does did how why what when where can could would should will please explain explanation tell about give me more again show display repeat image images picture pictures diagram diagrams visual visuals photo photos chapter lesson learning understand help also now example examples happen happens happening work works mean means difference between".split())
STOP.update({"another", "same", "continue", "elaborate", "detail", "details"})
ALIASES = {"gravitational": "gravity", "gravitation": "gravity", "forces": "force", "pushing": "push", "pushes": "push", "pulling": "pull", "pulls": "pull", "falling": "fall", "falls": "fall", "objects": "object", "fractions": "fraction", "plants": "plant"}
GENERIC_DESCRIPTION = re.compile(r"^(?:image|picture|photo|diagram|png|jpe?g|webp|gif|file|image/(?:png|jpeg|webp))$", re.I)


def tokens(text):
    return {ALIASES.get(word, word) for word in re.findall(r"[^\W\d_]+", (text or "").casefold()) if word not in STOP and len(word) > 2}


def block_text(blocks):
    return " ".join(" ".join([str(block.get("text", "")), str(block.get("title", "")), str(block.get("description", "")),
                               str(block.get("caption", "")), *[str(item) for item in block.get("items", [])]]) for block in blocks or [])[:6000]


def description(resource):
    def useful(value): return bool(value and value.strip() and not GENERIC_DESCRIPTION.fullmatch(value.strip().strip('.')))
    alt = resource.alt_text if useful(resource.alt_text) else resource.description if useful(resource.description) else resource.title
    caption = resource.caption_or_transcript if useful(resource.caption_or_transcript) else resource.description if useful(resource.description) else resource.title
    return (alt or "Learning illustration")[:1000], (caption or "Learning illustration")[:2000]


def none(reason):
    return {"schema_version": 1, "resource_id": None, "resource_version": None, "display_mode": "none", "reason": reason, "displayed": False, "reference_message_id": None}


def is_visual(resource):
    return resource.type in {"image", "diagram"} or resource.type in {"video", "animation"} and getattr(resource, "mime_type", None) == "image/gif"


def decide_image(resources, question, answer, *, previous_question="", grade="", objective="", subtopic_ids=(), history=()):
    explicit = bool(re.search(r"\b(?:show|display|repeat|see|view)\b.{0,50}\b(?:image|picture|diagram|photo|visual)\b|\b(?:image|picture|diagram|photo|visual)\b.{0,30}\b(?:again|please)\b", question, re.I))
    anchors = tokens(question)
    if not anchors:
        anchors = tokens(previous_question)
    answer_tokens = tokens(answer[:1800])
    grade_match = re.search(r"\b(?:grade|class|level)\s*(\d+|kg)\b", grade, re.I)
    ranking = []
    for resource in resources:
        if not is_visual(resource) or not resource.published or resource.availability != "available":
            continue
        media = " ".join(filter(None, [resource.title, resource.description, resource.alt_text, resource.caption_or_transcript, resource.accessibility_note]))
        media_grades = re.findall(r"\b(?:grade|class|level)\s*(\d+|kg)\b", media, re.I)
        if grade_match and media_grades and grade_match.group(1).casefold() not in {value.casefold() for value in media_grades}:
            continue
        descriptive = tokens(media); title_tokens = tokens(resource.title)
        overlap = anchors & descriptive
        # A question-specific concept match is mandatory. Generic answer words or
        # association alone cannot make a push/pull image illustrate gravity.
        if not overlap or len(overlap) / max(1, len(anchors)) < 0.5:
            continue
        if not explicit and not (overlap & answer_tokens):
            continue
        score = 8 * len(overlap) / len(anchors) + 3 * len(overlap & title_tokens)
        score += min(2, len(descriptive & answer_tokens) / 3)
        score += min(1, len(descriptive & tokens(objective)) / 3)
        score += 1 if str(resource.id) in subtopic_ids else 0
        ranking.append((score, str(resource.id), resource, sorted(overlap)))
    if not ranking:
        return none("No eligible image sufficiently matches the current concept and teaching objective.")
    _, _, selected, matched = sorted(ranking, key=lambda row: (-row[0], row[1]))[0]
    prior = next((item for item in reversed(list(history)) if item.get("resource_id") == str(selected.id)
                  and item.get("resource_version") == selected.version and item.get("display_mode") == "inline" and not item.get("failed")), None)
    mode = "inline" if explicit or prior is None else "reference earlier" if prior.get("displayed") else "none"
    if mode == "none":
        return none("An image for this concept is already being offered with an earlier answer.")
    return {"schema_version": 1, "resource_id": str(selected.id), "resource_version": selected.version, "display_mode": mode,
            "reason": ("Explicit image request. " if explicit else "") + "Matches " + ", ".join(matched) + " in the question and explanation; authorized curriculum path and grade suitability checked.",
            "reference_message_id": prior.get("message_id") if mode == "reference earlier" else None, "displayed": False}
