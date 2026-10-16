"""Pure routing over the shared trusted mathematics registry."""
import re
from app.contracts.math_templates import TEMPLATES
from app.contracts.decisions import RenderingDecision, VisualHistoryTurn


MATH_RULES = (
    (r"perpendicular bisector|bisect.*segment", "perpendicular_bisector"),
    (r"perpendicular.*line|line.*perpendicular", "perpendicular_lines"),
    (r"parallel.*line|line.*parallel", "parallel_lines"),
    (r"triangle.*(?:angle|vertic|construct|drag)|(?:angle|vertic|construct).*triangle", "triangle_angles"),
    (r"(?:circle|circular).*(?:radius|centre|center|construct)|(?:radius|construct).*circle", "circle_geometry"),
    (r"\b(?:sin|cos)\s*(?:\(?\s*x|\()|\b(?:sine|cosine)\b.*(?:graph|function|wave)|(?:graph|plot).*\b(?:sine|cosine)\b", "trigonometric_function"),
    (r"quadratic|parabola|x\s*(?:\^\s*2|²)", "quadratic_function"),
    (r"slope|linear (?:function|equation)|straight.line.*(?:graph|equation)|y\s*=\s*[^\n]*x", "linear_function"),
    (r"coordinate|plot.*point|point.*plane", "coordinate_points"),
    (r"fraction|\b\d+\s*/\s*\d+\b|quarters?|halves|thirds?", "fraction_bar"),
    (r"number line", "number_line"),
    (r"ruler|measure.*(?:length|line)|length.*measure", "ruler_measurement"),
    (r"count\b|counting|groups? of \d|group \d|grouping|\d+ objects", "counting_groups"),
    (r"(?:draw|explore|show|shape).*(?:triangle|rectangle|circle)|\bshapes?\b", "shape_explorer"),
    (r"(?:draw|explore|construct).*segment", "segment_geometry"),
)


def matching_templates(question: str) -> list[str]:
    q = question.casefold()
    result = []
    for pattern, template in MATH_RULES:
        if re.search(pattern, q):
            selected = "fraction_circle" if template == "fraction_bar" and re.search(r"circle|pizza", q) else template
            if selected not in result:
                result.append(selected)
    if "trigonometric_function" in result or "quadratic_function" in result:
        result = [name for name in result if name != "linear_function"]
    if any(name in result for name in ("triangle_angles", "circle_geometry")):
        result = [name for name in result if name != "shape_explorer"]
    return result


def decide_visual(question: str, level: int | None = None, history: list[VisualHistoryTurn] | None = None) -> RenderingDecision:
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
        for pattern, template in MATH_RULES:
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
