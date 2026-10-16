"""Deterministic policy observations captured before B15 extraction; no external I/O."""
from dataclasses import asdict
from types import SimpleNamespace
from uuid import UUID

from app.modules.application.recommendations.evaluation import evaluate
from app.modules.application.recommendations.selection import learning_need
from app.modules.application.recommendations.image_selection import decide_image
from app.modules.functional.curriculum.teaching_context import TeachingContext
from app.modules.application.teaching.profiles import profile
from app.modules.application.teaching.resolution import resolve
from app.modules.application.teaching.capabilities import unsupported_capability
from app.modules.application.teaching.output_guard import has_forbidden_authority_claim
from app.modules.application.teaching.math_visuals import decide_visual
from app.modules.application.teaching.simulations import select_engine


def observations():
    image = SimpleNamespace(id="image", type="image", title="Gravity falling objects", description="Gravity pulls objects down.",
        alt_text="Gravity falling objects", caption_or_transcript=None, accessibility_note=None,
        published=True, availability="available", version=2)
    first = decide_image([image], "Explain gravity", "Gravity pulls objects down.")
    history = [{**first, "message_id": "previous", "displayed": True}]
    context = TeachingContext({"subtopic_id": UUID(int=1)}, {"curriculum": "STEM", "level": "Grade 2",
        "subject": "Science", "topic": "Gravity", "subtopic": "Falling"}, 3, None, None)
    other = TeachingContext({"subtopic_id": UUID(int=2)}, {**context.names, "curriculum": "Other"}, 3, None, None)
    resolutions = []
    for question, paths in [("Explain gravity", [context]), ("Explain gravity", [other, context]), ("Explain oceans", [context])]:
        value = resolve(question, paths)
        resolutions.append(dict(status=value.status, context=str(value.context.ids["subtopic_id"]) if value.context else None,
            candidates=[str(item.ids["subtopic_id"]) for item in value.candidates]))
    questions = ["text only", "Compare monthly rainfall", "Explain fractions using pizza", "Graph a quadratic",
        "Show a perpendicular bisector", "Plot sine function", "Explain evaporation", "Count 5 objects"]
    simulations = ["Explain gravity", "Simulate a falling ball", "Create a 3d solar system simulation", "Build a quiz game",
        "Using matter.js create a force explainer", "Using three.js show me the world", "Create a rive animation",
        "Create a canvas animation", "Create a phaser game", "Create an interactive fraction graph",
        "Explain gravity with no animation", "Explain gravity with no animations"]
    capabilities = ["Explain a book", "Quote the textbook page source", "Grade my homework", "Read this pdf",
        "Watch this video", "Update my progress"]
    return dict(
        recommendations=evaluate(), profiles=[asdict(profile(None, label)) for label in ["KG", "Grade 1", "Grade 5", "Grade 9", "unknown"]],
        resolutions=resolutions,
        intents=[learning_need(q, "Explain gravity") for q in ["Explain gravity", "Show a gravity video", "Test my understanding",
            "I need a tutor", "Explain gravity; I do not want a tutor", "Tell me more"]],
        images=[first, decide_image([], "Explain gravity", "Gravity pulls."),
            decide_image([image], "Explain gravity", "Gravity pulls objects down.", history=history),
            decide_image([image], "Show the gravity image again", "Gravity pulls objects down.", history=history)],
        visuals=[dict(question=q, level=level, decision=decide_visual(q, level)) for q in questions for level in [None, 1, 5]],
        simulations=[dict(question=q, engine=select_engine(q)) for q in simulations],
        capabilities=[asdict(value) if (value := unsupported_capability(q)) else None for q in capabilities],
        authority=[has_forbidden_authority_claim(q) for q in ["Gravity pulls objects down.", "According to your textbook", "Your official grade is 90", "https://example.test"]],
    )
