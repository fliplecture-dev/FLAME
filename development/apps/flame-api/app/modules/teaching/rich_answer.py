"""F11 additive rich format. Only validated data, never executable model output."""
import json
from uuid import uuid4

from pydantic import TypeAdapter, ValidationError

from app.modules.teaching.gateway import GatewayError
from app.modules.teaching.schemas import LearningBlock

INSTRUCTION = r'''Format the teaching answer as Markdown. Use headings sparingly, GFM tables
or checklists only when useful, fenced code with a language, $$...$$ for inline math,
and $$ on separate lines for display math. Single dollar signs are literal currency.
Use TeX math delimiters for equations, fractions, algebra and calculations; never use
code fences or inline backticks for mathematical expressions. Use \frac{a}{b} for fractions.
Fenced code is only for actual programming source, with its programming language.
Never emit HTML, JSX, scripts, images or iframes. Code is displayed, never run.
When a chart helps, return ONLY a JSON object {"format":"flame-rich-1","blocks":[...]}.
Blocks can be {"kind":"markdown","text":"..."} or
{"kind":"chart","chartType":"bar|line|pie","title":"...","description":"...",
"xKey":"category","xLabel":"...","yLabel":"...","illustrative":true,
"series":[{"key":"value","label":"..."}],"data":[{"category":"A","value":2}]}.
Use actual chartType bar, line or pie. Maximum 4 series and 50 rows; pie uses one series
with nonnegative values and a positive total. Keys are distinct ASCII letters/digits/underscores
starting with a letter. Every row has exactly xKey and series keys. Values are finite numbers.
Label invented example data illustrative=true; only use false for values supplied by the learner.
Do not fabricate measurements or learning progress. Maximum 30 blocks and 6000 total characters.
Keep all human-readable content within the teaching word limit; JSON syntax does not count.
Do not emit IDs or provenance. If separate flame-intent metadata is requested, append it
AFTER the complete Markdown answer or JSON object, never inside it.'''

_block = TypeAdapter(LearningBlock)


def parse_blocks(text: str) -> list[dict]:
    if text.startswith('{') or (text.startswith('```json') and '"format"' in text):
        try:
            raw = text
            if raw.startswith('```json') and raw.endswith('```'):
                raw = raw[len('```json'):-3].strip()
            def unique_object(pairs):
                result = {}
                for key, value in pairs:
                    if key in result:
                        raise ValueError("Duplicate JSON key")
                    result[key] = value
                return result
            envelope = json.loads(raw, object_pairs_hook=unique_object)
            if not isinstance(envelope, dict) or set(envelope) != {"format", "blocks"} or envelope["format"] != "flame-rich-1":
                raise ValueError("Invalid rich answer envelope")
            blocks = envelope["blocks"]
            if not isinstance(blocks, list) or not 1 <= len(blocks) <= 30:
                raise ValueError("Invalid block count")
            result = []
            for block in blocks:
                if not isinstance(block, dict) or block.get("kind") not in {"markdown", "chart", "math_visual"} or "id" in block:
                    raise ValueError("Invalid generated block")
                result.append(_block.validate_python({**block, "id": str(uuid4())}).model_dump(mode="json"))
            return result
        except (ValueError, TypeError, ValidationError, RecursionError):
            raise GatewayError("invalid_provider_output") from None
    return [{"id": str(uuid4()), "kind": "markdown", "text": text}]


def readable(blocks: list[dict]) -> str:
    """History/word guard projection includes chart labels and data within caller budgets."""
    parts = []
    for block in blocks:
        kind = block.get("kind")
        if kind in {"text", "markdown", "heading", "callout"}:
            parts.extend(str(block.get(key, "")) for key in ("title", "text"))
        elif kind == "list":
            parts.extend(block.get("items", []))
        elif kind == "table":
            parts.extend([block.get("caption", ""), *block.get("columns", [])])
            parts.extend(str(cell) for row in block.get("rows", []) for cell in row)
        elif kind == "chart":
            parts.extend(str(block.get(key, "")) for key in ("title", "description", "xLabel", "yLabel"))
            parts.extend(item.get("label", "") for item in block.get("series", []))
            parts.extend(str(cell) for row in block.get("data", []) for cell in row.values())
        elif kind == "math_visual":
            parts.extend(str(block.get(key, "")) for key in ("title", "description"))
            parts.append("Saved initial activity: " + str(block.get("template", "")))
            parts.append(json.dumps(block.get("parameters", {}), ensure_ascii=False, separators=(",", ":")))
    return " ".join(parts).strip()
