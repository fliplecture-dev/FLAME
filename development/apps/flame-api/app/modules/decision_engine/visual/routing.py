"""One response policy shared by prompts, finalization and simulation delivery."""
import re

from app.contracts.decisions import RenderingDecision, VisualHistoryTurn, VisualRoutingDecision
from app.modules.decision_engine import POLICY_VERSION
from app.modules.decision_engine.visual.keywords import VISUAL_WORDS, normalized, text_requested, visual_requested
from app.modules.decision_engine.visual.mathematics import decide_visual, matching_templates
from app.modules.decision_engine.visual.simulation import select_engine
from app.modules.decision_engine.visual.graphs import GRAPH_TEMPLATES, graph_requested, fallback_graph

MATH = re.compile(r"\b(?:maths?|mathematics|arithmetic|algebra|geometr\w*|fractions?|quarters?|halves|thirds?|equations?|calculat\w*|solve|addition|subtraction|multipli\w*|division|counting|coordinates?|quadratic|parabola|trigonometr\w*|sine|cosine|slope|number line|perpendicular|parallel lines|triangle.*angles?)\b|\d\s*[-+×÷=*/]\s*\d", re.I)
SCIENCE = re.compile(r"\b(?:sciences?|scientific|physic\w*|chemistry|biology|motion|gravity|forces?|energy|matter|light|sound|electric\w*|magnet\w*)\b", re.I)


def _refers_to_previous(question: str) -> bool:
    """Only topic-free requests may inherit a topic; new nouns stop inheritance."""
    q = re.sub(r"\b[23][ -]?d\b", " ", normalized(question))
    q = re.sub(r"\b" + VISUAL_WORDS + r"\b", " ", q)
    words = set(re.findall(r"[a-z]+", q))
    generic = set("please can could would will you i want need like to for of with about on in a an the it its this that these those same previous last above response answer topic explanation example now again more me my us using use based turn into and or some add controls activity activities interaction diagram model scene matter three js r3f react fiber phaser rive html canvas svg tell explain explore change".split())
    return bool(question.strip()) and words <= generic


def _previous_topic(history: list[VisualHistoryTurn] | None) -> str:
    # Read only bounded, owned conversation data supplied by the application.
    # Stop at a new subject rather than searching past it for an older physics turn.
    for turn in reversed((history or [])[-8:]):
        user = " ".join(str(b.get("text", "")) for b in turn.get("user", []) if b.get("kind") in {"text", "markdown"})[:2000]
        if not user:
            return ""
        if _refers_to_previous(user):
            continue
        return user
    return ""


def decide_response_visual(question: str, *, mode: str = "curiosity", context_names: dict[str, str | None] | None = None,
                           level: int | None = None, history: list[VisualHistoryTurn] | None = None) -> VisualRoutingDecision:
    names = context_names or {}
    scope = " ".join(filter(None, (names.get(key) for key in ("subject", "domain", "topic", "subtopic"))))
    requested = visual_requested(question)
    previous = _previous_topic(history) if requested and _refers_to_previous(question) else ""
    if not previous and graph_requested(question) and _refers_to_previous(question) and MATH.search(scope):
        previous = scope
    resolved_question = question + "\n" + previous if previous else question
    math_subject = bool(MATH.search(names.get("subject") or ""))
    science = mode == "study" and not math_subject and bool(SCIENCE.search(scope))
    base = decide_visual(resolved_question, level, history)
    # Formula notation remains available in text mode; activities and charts do not.
    reason = "Explain in text unless a mathematical goal or a visual request applies."
    rendering: RenderingDecision = dict(mode="text", preferred_template=None, allowed_templates=[], max_activities=0,
                                        allow_charts=False, reason=reason)
    kind, engine, media_first = "text", None, False
    if text_requested(question):
        reason = "The learner requested text without visual activities."
    elif MATH.search(resolved_question) or (not science and (math_subject or base["mode"] == "math" or graph_requested(question) and base["mode"] != "chart")):
        kind, reason = "math", "Explain mathematics with TeX notation and suitable trusted activities."
        from app.contracts.math_templates import TEMPLATES
        eligible = [name for name, spec in TEMPLATES.items() if level is None or spec["minLevel"] <= level]
        matched = matching_templates(resolved_question)
        allowed = [name for name in matched if name in eligible]
        if matched and not allowed:
            kind, reason = "text", "The requested activity exceeds the known teaching level. Explain using text and notation."
        else:
            preferred = allowed[0] if allowed else base["preferred_template"]
            rendering = dict(mode="math", preferred_template=preferred, allowed_templates=allowed or eligible,
                             max_activities=3, allow_charts=bool(re.search(r"\b(?:data|statistics|bar chart|pie chart|rainfall|survey)\b", resolved_question, re.I)), reason=reason)
            if graph_requested(question):
                rendering["require_graph"] = True
                graph_templates = [name for name in rendering["allowed_templates"] if name in GRAPH_TEMPLATES]
                # A topic-free maths graph request uses the coordinate viewport.
                if not matched and not graph_templates:
                    graph_templates = [name for name in eligible if name in GRAPH_TEMPLATES]
                if graph_templates:
                    fallback = fallback_graph(resolved_question, graph_templates[0])
                    if fallback:
                        rendering["fallback_graph"] = fallback
                # Explicit graphs are response charts, not interactive math activities.
                rendering.update(mode="chart", allowed_templates=[], preferred_template=None,
                                 max_activities=0, allow_charts=True)
    elif science and not requested:
        reason = "Study science uses text until the learner asks for a visual."
    elif requested:
        engine = select_engine(question, context=" ".join(filter(None, (previous, scope))))
        if science and engine not in {"matter", "three", "r3f"}:
            engine = None
        # Reuse an authored science interactive even when procedural generation is unsuitable.
        if engine is not None or science:
            kind, media_first = "simulation", True
            reason = "Use a matching published simulation first; otherwise generate with a suitable engine."
        elif base["mode"] == "chart":
            rendering, reason = base, base["reason"]
    elif not science and base["mode"] == "chart":
        rendering, reason = base, base["reason"]
    if kind == "text" and rendering["mode"] == "text":
        rendering["reason"] = reason
    result: VisualRoutingDecision = dict(policy_version=POLICY_VERSION, response_kind=kind, visual_requested=requested,
                simulation_engine=engine, media_first=media_first, rendering=rendering, reason=reason,
                allow_media_recommendations=not (text_requested(question) or kind == "simulation" or science and kind == "text" and not requested))
    if kind == "simulation" and previous:
        result["simulation_question"] = resolved_question
    return result
