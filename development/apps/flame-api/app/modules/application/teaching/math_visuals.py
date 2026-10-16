"""F12 trusted template contract and deterministic rendering policy; no code evaluation."""
import json
import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.contracts.math_templates import TEMPLATES
from app.contracts.decisions import RenderingDecision
from app.modules.decision_engine.visual.mathematics import decide_visual


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


def decision_instruction(decision: RenderingDecision) -> str:
    # Parameter examples are data, not executable formulas or library props.
    specs = {name: {"parameters": {key: item["default"] for key, item in TEMPLATES[name]["parameters"].items()},
                    "bounds": {key: item.get("options", [item.get("min"), item.get("max")]) for key, item in TEMPLATES[name]["parameters"].items()}}
             for name in decision["allowed_templates"]}
    return ("\nRendering policy (server-owned): " + json.dumps(decision, ensure_ascii=False) +
        f'\nUse the flame-rich-1 envelope with at most {decision.get("max_activities", 1)} distinct mathematical activities. Each '
        'math_visual block: {"kind":"math_visual","version":1,"template":"allowed_name",'
        '"title":"short title","description":"short instructions","parameters":{...}}. '
        'Include an explanatory markdown block. Use exactly the listed parameter keys and numeric bounds; '
        'counts/fraction parts/number-line bounds are integers. Fraction numerator cannot exceed denominator. '
        'Initial geometry points must form valid constructions. Prefer the specified template when mode=math. '
        'For triangle angle requests choose coordinates matching the requested angles, not generic defaults. '
        'Trigonometric graphs use y=a*sin(k*(x-h))+d or y=a*cos(k*(x-h))+d; angles are radians. '
        'Use function=cos when cosine is requested. Equations themselves belong in TeX math delimiters, '
        'not programming code fences or ASCII-art drawings. '
        'Mode=text forbids all charts/activities but keeps TeX notation. Mode=chart uses a chart. '
        'Mode=math combines an explanation and TeX formulas with helpful allowed activities; '
        'When require_graph=true, you MUST include a valid chart block in the same '
        'flame-rich-1 answer, alongside the explanation. The graph is rendered immediately inline '
        'in the answer viewport using the response chart renderer, not a code editor, sandbox '
        'or mathematical activity. Supply numeric data points matching the requested equation; '
        'do not substitute ASCII art, a code fence, an external link or a promise to show it later. '
        'use different templates only when each addresses the question. Charts also require allow_charts=true. '
        'Mode=auto uses semantic meaning (including non-English questions) to select an allowed template only '
        'when useful; plain prose/formulas need no activity. Primary shapes use shape_explorer, mathematical '
        'relationships use geometry, coordinate/function exploration uses coordinate/function templates. '
        'Never emit engine/library names, executable formulas, arbitrary props or learner-adjusted state. '
        'All existing topic, age, word and output limits apply. Allowed template defaults/bounds: ' + json.dumps(specs, separators=(",", ":")))


def apply_decision(blocks: list[dict], decision: RenderingDecision) -> list[dict]:
    """Do not persist an unsuitable visual even when the provider ignores routing guidance."""
    result, used_templates = [], set()
    maximum = min(3, max(0, decision.get("max_activities", 1)))
    for block in blocks:
        if block["kind"] == "chart" and (decision["mode"] == "text" or decision["mode"] == "math" and not decision.get("allow_charts", False)):
            continue
        if block["kind"] == "math_visual":
            if block["template"] not in decision["allowed_templates"] or block["template"] in used_templates or len(used_templates) >= maximum:
                continue
            used_templates.add(block["template"])
        result.append(block)
    if decision.get("require_graph") and not any(block.get("kind") == "chart" for block in result):
        fallback = decision.get("fallback_graph")
        if fallback and fallback.get("kind") == "chart" and decision.get("allow_charts"):
            from uuid import uuid4
            from app.modules.application.teaching.schemas import ChartBlock
            result.append(ChartBlock(id=str(uuid4()), **fallback).model_dump(mode="json"))
        else:
            # Never save a text-only success or invent a different function.
            from app.modules.application.teaching.gateway import GatewayError
            raise GatewayError("invalid_provider_output")
    if not result:
        from uuid import uuid4
        result = [dict(id=str(uuid4()), kind="markdown", text="A suitable visual is unavailable. Please ask for a simpler explanation.")]
    return result
