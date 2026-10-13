"""Optional intent metadata in the existing answer call; never selects catalogue IDs."""
import json
import re

INTENTS = {"explain", "demonstrate", "practise", "human_help", "follow_up"}
INSTRUCTION = '''After the teaching answer, append exactly one <flame-intent> JSON object </flame-intent>.
Use keys intent (explain/demonstrate/practise/human_help/follow_up), concept (short specific concept), language (ISO language code).
Infer from the current question, recent conversation and selected curriculum. human_help requires an explicit human/tutor request.
Do not include candidate IDs, URLs, availability, recommendations or personal information. This metadata is separate from the teaching answer.'''


def split_intent(text):
    marker = text.find("<flame-intent>")
    if marker < 0:
        return text, None
    answer = text[:marker].rstrip()
    try:
        raw = text[marker + len("<flame-intent>"):].split("</flame-intent>", 1)[0]
        data = json.loads(raw)
        if (not isinstance(data, dict) or data.get("intent") not in INTENTS or
                not isinstance(data.get("concept"), str) or not 1 <= len(data["concept"]) <= 100 or
                not re.fullmatch(r"[a-z]{2,3}", data.get("language", ""))):
            return answer, None
        return answer, {key: data[key] for key in ("intent", "concept", "language")}
    except (ValueError, TypeError):
        return answer, None
