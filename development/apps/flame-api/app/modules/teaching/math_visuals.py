"""F12 trusted template contract and deterministic rendering policy; no code evaluation."""
import json
import math
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

TEMPLATES = json.loads(Path(__file__).with_name("math_templates.json").read_text(encoding="utf-8"))


class MathVisualBlock(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["math_visual"]
    version: Literal[1]
    template: str
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=500)
    parameters: dict

    @model_validator(mode="before")
    @classmethod
    def strict_version(cls, value):
        if isinstance(value, dict) and type(value.get("version")) is not int:
            raise ValueError("Mathematics version must be an integer")
        return value

    @model_validator(mode="after")
    def validate_spec(self):
        if self.template not in TEMPLATES:
            raise ValueError("Unknown mathematics template")
        fields = TEMPLATES[self.template]["parameters"]
        if set(self.parameters) != set(fields):
            raise ValueError("Parameters must match the trusted template")
        for key, spec in fields.items():
            value = self.parameters[key]
            if "options" in spec:
                if type(value) is not str or value not in spec["options"]:
                    raise ValueError("Unsupported parameter option")
            elif (type(value) not in (int, float) or not spec["min"] <= value <= spec["max"] or
                  not math.isfinite(value) or
                  (spec["step"] == 1 and value != int(value)) or
                  abs(value - round(value, 3)) > 1e-8):
                raise ValueError("Mathematical parameter outside bounds")
        p = self.parameters
        if self.template.startswith("fraction_") and p["numerator"] > p["denominator"]:
            raise ValueError("Shaded parts cannot exceed equal parts")
        if self.template == "number_line" and not (p["start"] < p["end"] and p["start"] <= p["value"] <= p["end"]):
            raise ValueError("Number line bounds must contain the point")
        if "bx" in p and math.hypot(p["ax"] - p["bx"], p["ay"] - p["by"]) < .1:
            raise ValueError("Construction endpoints must be distinct")
        if self.template == "triangle_angles" and abs((p["bx"]-p["ax"])*(p["cy"]-p["ay"])-(p["by"]-p["ay"])*(p["cx"]-p["ax"])) < .1:
            raise ValueError("Initial triangle must not be degenerate")
        return self


def decide_visual(question: str, level: int | None = None, history: list[dict] | None = None) -> dict:
    """High-confidence lexical hints plus same-call semantic selection for other languages.

    Question text never supplies executable parameters or changes template eligibility.
    Only a narrowly phrased follow-up can inherit the previous saved activity.
    """
    q = question.casefold()
    allowed = [name for name, spec in TEMPLATES.items() if level is None or spec["minLevel"] <= level]
    mode, preferred, reason = "auto", None, "Use an activity only when it helps this learning question."
    if re.search(r"\b(text only|just text|no (?:visuals?|diagrams?|graphs?|charts?|activities)|without (?:a )?(?:visual|diagram|graph|chart))\b", q):
        mode, reason = "text", "The learner requested text only."
    elif re.search(r"\b(?:rainfall|sales|survey|monthly|statistics|dataset|data chart|bar chart|pie chart)\b", q) and not re.search(r"\b(?:function|equation|slope|parabola)\b", q):
        mode, reason = "chart", "Compare observed or illustrative data with the existing chart renderer."
    else:
        rules = [
            (r"perpendicular bisector|bisect.*segment", "perpendicular_bisector"),
            (r"perpendicular.*line|line.*perpendicular", "perpendicular_lines"),
            (r"parallel.*line|line.*parallel", "parallel_lines"),
            (r"triangle.*(?:angle|vertic|construct|drag)|(?:angle|vertic|construct).*triangle", "triangle_angles"),
            (r"(?:circle|circular).*(?:radius|centre|center|construct)|(?:radius|construct).*circle", "circle_geometry"),
            (r"\b(?:sin|cos)\s*(?:\(?\s*x|\()|\b(?:sine|cosine)\b.*(?:graph|function|wave)|(?:graph|plot).*\b(?:sine|cosine)\b", "trigonometric_function"),
            (r"quadratic|parabola|x\s*(?:\^\s*2|²)", "quadratic_function"),
            (r"slope|linear function|straight.line.*(?:graph|equation)|y\s*=\s*[^\n]*x", "linear_function"),
            (r"coordinate|plot.*point|point.*plane", "coordinate_points"),
            (r"fraction|\b\d+\s*/\s*\d+\b|quarters?|halves|thirds?", "fraction_bar"),
            (r"number line", "number_line"),
            (r"ruler|measure.*(?:length|line)|length.*measure", "ruler_measurement"),
            (r"count\b|counting|groups? of \d|group \d|grouping|\d+ objects", "counting_groups"),
            (r"(?:draw|explore|show|shape).*(?:triangle|rectangle|circle)|\bshapes?\b", "shape_explorer"),
            (r"(?:draw|explore|construct).*segment", "segment_geometry"),
        ]
        for pattern, template in rules:
            if re.search(pattern, q):
                preferred = "fraction_circle" if template == "fraction_bar" and re.search(r"circle|pizza", q) else template
                mode, reason = "math", "Match the learning goal to a reviewed activity template."
                break
        if preferred is None and re.fullmatch(r"\s*(?:explain|show|change|explore|tell me more about) (?:that|this|the same)(?: activity| graph| visual| example)?[.!?]*\s*", q):
            for turn in reversed((history or [])[-8:]):
                previous = next((b.get("template") for b in turn.get("assistant", []) if b.get("kind") == "math_visual" and b.get("template") in allowed), None)
                if previous:
                    preferred, mode, reason = previous, "math", "Continue the saved mathematical activity."
                    break
        if preferred and preferred not in allowed:
            preferred, mode, reason = None, "text", "The requested activity exceeds the known teaching level; give an age-suitable explanation."
    if mode == "math":
        allowed = [preferred]
    elif mode in {"text", "chart"}:
        allowed = []
    return dict(mode=mode, preferred_template=preferred, allowed_templates=allowed, reason=reason)


def decision_instruction(decision: dict) -> str:
    # Parameter examples are data, not executable formulas or library props.
    specs = {name: {"parameters": {key: item["default"] for key, item in TEMPLATES[name]["parameters"].items()},
                    "bounds": {key: item.get("options", [item.get("min"), item.get("max")]) for key, item in TEMPLATES[name]["parameters"].items()}}
             for name in decision["allowed_templates"]}
    return ("\nRendering policy (server-owned): " + json.dumps(decision, ensure_ascii=False) +
        '\nFor an allowed mathematical activity use the flame-rich-1 envelope with at most ONE '
        'math_visual block: {"kind":"math_visual","version":1,"template":"allowed_name",'
        '"title":"short title","description":"short instructions","parameters":{...}}. '
        'Include an explanatory markdown block. Use exactly the listed parameter keys and numeric bounds; '
        'counts/fraction parts/number-line bounds are integers. Fraction numerator cannot exceed denominator. '
        'Initial geometry points must form valid constructions. Prefer the specified template when mode=math. '
        'For triangle angle requests choose coordinates matching the requested angles, not generic defaults. '
        'Trigonometric graphs use y=a*sin(k*(x-h))+d or y=a*cos(k*(x-h))+d; angles are radians. '
        'Use function=cos when cosine is requested. Equations themselves belong in TeX math delimiters, '
        'not programming code fences or ASCII-art drawings. '
        'Mode=text forbids all charts/activities. Mode=chart uses a chart, not a math activity. '
        'Mode=auto uses semantic meaning (including non-English questions) to select an allowed template only '
        'when useful; plain prose/formulas need no activity. Primary shapes use shape_explorer, mathematical '
        'relationships use geometry, coordinate/function exploration uses coordinate/function templates. '
        'Never emit engine/library names, executable formulas, arbitrary props or learner-adjusted state. '
        'All existing topic, age, word and output limits apply. Allowed template defaults/bounds: ' + json.dumps(specs, separators=(",", ":")))


def apply_decision(blocks: list[dict], decision: dict) -> list[dict]:
    """Do not persist an unsuitable visual even when the provider ignores routing guidance."""
    result, math_count = [], 0
    for block in blocks:
        if block["kind"] == "chart" and decision["mode"] in {"text", "math"}:
            continue
        if block["kind"] == "math_visual":
            if block["template"] not in decision["allowed_templates"] or math_count:
                continue
            math_count += 1
        result.append(block)
    if not result:
        from uuid import uuid4
        result = [dict(id=str(uuid4()), kind="markdown", text="A suitable visual is unavailable. Please ask for a simpler explanation.")]
    return result
