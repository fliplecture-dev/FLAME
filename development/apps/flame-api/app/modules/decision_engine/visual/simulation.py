"""Pure opt-in simulation engine selection; no generation or transient cache."""
import re
from app.contracts.decisions import SimulationEngine
from app.modules.decision_engine.visual.keywords import visual_requested


def select_engine(question: str, *, context: str = "") -> SimulationEngine | None:
    """Conservative opt-in routing; normal explanation/math requests remain unchanged."""
    q = question.casefold()
    if not visual_requested(question):
        return None
    explicit = ((r"\bmatter(?:\.js)?\b", "matter"), (r"\b(?:r3f|react three fiber)\b", "r3f"),
                (r"\bthree(?:\.js)?\b", "three"), (r"\bphaser\b", "phaser"),
                (r"\brive\b", "rive"), (r"\b(?:html5|canvas|svg)\b", "html5"))
    for pattern, engine in explicit:
        if re.search(pattern, q):
            return engine
    q = q + " " + context.casefold()
    if re.search(r"\b(?:3[- ]?d|solar system|planet|molecule)\b", q):
        return "three"
    if re.search(r"\b(?:game|quiz game|platformer)\b", q):
        return "phaser"
    if re.search(r"\b(?:gravity|falling|collision|collid\w*|friction|physics|pendulum|ball|block|forces?|motion|velocity|mass|spring|momentum|acceleration|pressure|particles?)\b", q):
        return "matter"
    if re.search(r"\b(?:fractions?|counting|number line|coordinates?|functions?|geometry|triangles?|shapes?|graphs?)\b", q):
        return None  # Existing trusted F12 mathematics remains the default for these goals.
    return "html5" if re.search(r"\b(?:animat\w*|illustrat\w*)\b", q) else None
