"""B16 keyword routing, composition, catalogue-first delivery and generation guards."""
import json
import math
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.contracts.catalogue import CatalogueCandidate
from app.contracts.decisions import TeachingContext
from app.contracts.math_templates import TEMPLATES
from app.modules.decision_engine.visual.routing import decide_response_visual
from app.modules.decision_engine.visual.media import select_simulation
from app.modules.application.teaching.prompt import assemble, assemble_open_curiosity
from app.modules.application.teaching.math_visuals import apply_decision
from app.modules.application.teaching.answer_service import _answer
from app.modules.application.teaching.gateway import Generated, GatewayError
from app.modules.decision_engine.teaching.profiles import profile
from app.modules.application.teaching import simulation_router, visual_media
from app.modules.functional.resources import simulations as resource_simulations

SCIENCE = {"subject": "Science", "domain": "Physics", "topic": "Gravity", "subtopic": "Falling objects"}


def history_turn(question, answer="Gravity pulls objects toward Earth."):
    return {"user": [{"kind": "text", "text": question}], "assistant": [{"kind": "markdown", "text": answer}]}


@pytest.mark.parametrize("question,template,parameters", [
    ("Explain y=2x+1 using a graph", "linear_function", {"m": 2, "b": 1}),
    ("Plot y=-x+3", "linear_function", {"m": -1, "b": 3}),
    ("Graph y=1.5*x-2.5", "linear_function", {"m": 1.5, "b": -2.5}),
    ("Graph y=x^2-2x+1", "quadratic_function", {"a": 1, "b": -2, "c": 1}),
    ("Graph y=-2x²+x-1", "quadratic_function", {"a": -2, "b": 1, "c": -1}),
    ("Graph y=cos(x)", "trigonometric_function", {"function": "cos"}),
    ("Plot y=sin(x)", "trigonometric_function", {"function": "sin"}),
])
def test_requested_graph_survives_a_text_only_model_answer(question, template, parameters):
    prompt = assemble_open_curiosity(question, [])
    decision = prompt.rendering_decision
    assert decision["require_graph"] and decision["mode"] == "chart"
    assert decision["allowed_templates"] == [] and decision["max_activities"] == 0
    assert "MUST include" in prompt.messages[0]["content"]
    answer = _answer(uuid4(), None, Generated("This explains the requested function.", "stub", 10, 10), rendering_decision=decision)
    graph = next(b for b in answer["blocks"] if b["kind"] == "chart")
    assert graph["chartType"] == "line" and not graph["illustrative"]
    assert not any(b["kind"] == "math_visual" for b in answer["blocks"])
    for row in graph["data"]:
        x = row["x"]
        if template == "linear_function":
            expected = parameters["m"] * x + parameters["b"]
        elif template == "quadratic_function":
            expected = parameters["a"] * x * x + parameters["b"] * x + parameters["c"]
        else:
            expected = math.cos(x) if parameters["function"] == "cos" else math.sin(x)
        assert row["y"] == pytest.approx(expected, abs=1e-6)
    assert answer["blocks"][0]["kind"] == "markdown"
    # Already emitted graphs are retained without adding another copy.
    assert apply_decision(answer["blocks"], decision) == answer["blocks"]


def test_graph_followup_uses_maths_history_or_selected_topic_and_respects_opt_outs():
    history = [history_turn("Explain y=2x+1")]
    decision = decide_response_visual("Explain using a graph", history=history)["rendering"]
    assert next(row["y"] for row in decision["fallback_graph"]["data"] if row["x"] == 1) == 3
    selected = decide_response_visual("Explain using a graph", mode="study", context_names={"subject": "Mathematics", "topic": "Quadratic functions"}, level=5)
    assert selected["rendering"]["mode"] == "chart"
    assert next(row["y"] for row in selected["rendering"]["fallback_graph"]["data"] if row["x"] == 2) == 4
    for q in ["Graph y=x, text only", "Don't graph y=x", "No graphs for y=x"]:
        assert decide_response_visual(q)["rendering"]["mode"] == "text"
    assert not decide_response_visual("Graph a quadratic", level=1)["rendering"].get("require_graph")


@pytest.mark.parametrize("question", ["Graph y=20x+1", "Graph y=x^3", "Graph y=2x3", "Graph y=(x+1)^2", "Graph 2sin(x)"])
def test_graph_fallback_never_substitutes_an_unparsed_or_out_of_bounds_function(question):
    decision = decide_response_visual(question)["rendering"]
    assert decision["require_graph"] and "fallback_graph" not in decision
    with pytest.raises(GatewayError):
        apply_decision([dict(id="text", kind="markdown", text="An explanation.")], decision)


def test_fraction_graph_can_use_a_valid_chart_and_data_graphs_keep_chart_routing():
    decision = decide_response_visual("Explain fractions using a graph")["rendering"]
    chart = dict(id="chart", kind="chart", chartType="bar")
    assert decision["require_graph"] and decision["allow_charts"]
    assert apply_decision([chart], decision) == [chart]
    assert decide_response_visual("Graph rainfall data")["rendering"]["mode"] == "chart"


@pytest.mark.parametrize("question", ["interactivity", "create", "create interactivity", "make it interactive", "show me", "Please create a simulation based on the previous response"])
def test_short_physics_followups_keep_the_recent_topic(question):
    history = [history_turn("Explain gravity in physics")]
    plan = assemble_open_curiosity(question, history).visual_routing
    assert plan["response_kind"] == "simulation" and plan["simulation_engine"] == "matter"
    assert plan["simulation_question"] == question + "\nExplain gravity in physics"
    assert select_simulation([candidate()], plan["simulation_question"]) is not None


def test_followup_dimensions_maths_opt_outs_and_subject_changes():
    gravity = [history_turn("Explain gravity")]
    assert decide_response_visual("show this in 3D", history=gravity)["simulation_engine"] == "three"
    solar = [history_turn("Explain the 3D solar system")]
    assert decide_response_visual("create interactivity", history=solar)["simulation_engine"] == "three"
    maths = [history_turn("Explain fractions")]
    assert decide_response_visual("make it interactive", history=maths)["rendering"]["allowed_templates"] == ["fraction_bar"]
    for question in ["Tell me more", "create interactivity, text only", "don't show it"]:
        assert decide_response_visual(question, history=gravity)["response_kind"] == "text"
    for history in [[], gravity + [history_turn("Explain a poem", "A poem uses rhythm.")]]:
        plan = decide_response_visual("create interactivity", history=history)
        assert plan["response_kind"] == "text" and "simulation_question" not in plan
    plan = decide_response_visual("create an interactive ocean scene", history=gravity)
    assert plan["simulation_engine"] is None and "simulation_question" not in plan
    assert "simulation_question" not in decide_response_visual("show fractions", history=gravity)
    chain = gravity + [history_turn("tell me more"), history_turn("make it interactive")]
    assert decide_response_visual("create", history=chain)["simulation_engine"] == "matter"


@pytest.mark.parametrize("word", ["show", "SHOWME", "show me", "simulate", "visualization", "visual", "visualisation", "interactive", "interactivity", "create"])
def test_all_requested_keywords_use_selected_physics_context(word):
    route = decide_response_visual(word, mode="study", context_names=SCIENCE)
    assert route["response_kind"] == "simulation" and route["simulation_engine"] == "matter"
    assert route["media_first"] and not route["allow_media_recommendations"]


@pytest.mark.parametrize("question", ["Explain gravity", "Why do objects fall?", "Tell me about creatures"])
def test_science_explanations_without_a_visual_request_are_text(question):
    route = decide_response_visual(question, mode="study", context_names=SCIENCE)
    assert route["response_kind"] == "text"
    assert route["rendering"]["allowed_templates"] == [] and not route["allow_media_recommendations"]


@pytest.mark.parametrize("question", ["Show gravity, text only", "Create gravity with no animations", "Don't show gravity", "Simulate gravity without a visual", "No simulations of gravity", "Just text about fractions"])
def test_opt_out_has_priority_over_positive_keywords_and_mathematics(question):
    route = decide_response_visual(question, mode="study", context_names=SCIENCE)
    assert route["response_kind"] == "text" and route["simulation_engine"] is None
    assert not route["allow_media_recommendations"]


def test_math_combines_trusted_libraries_and_keeps_existing_level_limits():
    route = decide_response_visual("Explain fractions, triangle angles and a quadratic function", level=5)
    assert route["response_kind"] == "math" and route["simulation_engine"] is None
    decision = route["rendering"]
    assert {TEMPLATES[name]["engine"] for name in decision["allowed_templates"]} == {"konva", "jsxgraph", "mafs"}
    blocks = [{"id": "text", "kind": "markdown", "text": "$$1/2$$ and $$y=x^2$$."}]
    blocks += [dict(id=name, kind="math_visual", template=name) for name in decision["allowed_templates"]]
    result = apply_decision(blocks + blocks[1:], decision)
    assert len(result) == 4 and result[0] == blocks[0]
    assert decide_response_visual("Graph a quadratic", level=1)["rendering"]["allowed_templates"] == []
    assert decide_response_visual("Solve 2+2")["response_kind"] == "math"
    assert decide_response_visual("Explain algebra", mode="study", context_names={"subject": "Mathematics"})["response_kind"] == "math"
    assert decide_response_visual("Show a 3D solar system")["simulation_engine"] == "three"
    assert decide_response_visual("Show photosynthesis", mode="study", context_names={"subject": "Biology"})["simulation_engine"] is None


def test_study_prompt_and_output_filter_share_the_text_decision():
    context = TeachingContext({}, SCIENCE, 2, None, None)
    prompt = assemble("Explain gravity", context, profile(None, "Grade 2"), [])
    assert prompt.visual_routing["response_kind"] == "text"
    assert prompt.rendering_decision is prompt.visual_routing["rendering"]
    assert '"mode": "text"' in prompt.messages[0]["content"]
    blocks = [dict(id="t", kind="markdown", text="Gravity follows $$F=ma$$."), dict(id="c", kind="chart"), dict(id="m", kind="math_visual", template="fraction_bar")]
    assert apply_decision(blocks, prompt.rendering_decision) == blocks[:1]


def candidate(title="Gravity simulation", **changes):
    values = dict(id=uuid4(), kind="resource", type="interactive", mime_type="text/html", version=2,
        title=title, description="Gravity pulls falling objects down", availability_state="available", card={})
    return CatalogueCandidate(**(values | changes))


def test_catalogue_selection_requires_relevance_format_grade_and_language():
    gravity = candidate(languages=["en"], grade_min=0, grade_max=3)
    assert select_simulation([gravity], "Show gravity", grade="Grade 2", language="en") is gravity
    assert select_simulation([gravity], "Show me", topic="Gravity", grade="Grade 2", language="en") is gravity
    assert select_simulation([gravity], "Show evaporation") is None
    for row in [candidate(type="video"), candidate(mime_type="text/plain"), candidate(published=False), candidate(availability_state="unavailable")]:
        assert select_simulation([row], "Show gravity") is None
    assert select_simulation([gravity], "Show gravity", grade="Grade 8") is None
    assert select_simulation([gravity], "Show gravity", language="ta") is None
    assert select_simulation([gravity], "Show a 3D gravity simulation") is None
    three = candidate("3D gravity simulation")
    assert select_simulation([gravity, three], "Show a 3D gravity simulation") is three


def route_fixture(monkeypatch, question="Show gravity", *, saved=None, media=None):
    db = MagicMock()
    stored = SimpleNamespace(result=saved or {})
    db.scalar.side_effect = [SimpleNamespace(turn_number=1), SimpleNamespace(blocks=[{"text": question}]), stored]
    database = MagicMock()
    database.session.return_value.__enter__.return_value = db
    context = TeachingContext({"topic_id": uuid4(), "subtopic_id": uuid4()}, SCIENCE, 2, None, None)
    conversation = SimpleNamespace(mode="study", context_snapshot={}, revision=2)
    monkeypatch.setattr(simulation_router, "owned", lambda *a, **kw: conversation)
    monkeypatch.setattr(simulation_router, "load_context", lambda *a, **kw: context)
    library = MagicMock(return_value=media or (None, None))
    monkeypatch.setattr(simulation_router, "library_simulation", library)
    transient = MagicMock()
    transient.response_language.return_value = None
    transient.run.return_value = {"status": "pending"}
    monkeypatch.setattr(simulation_router, "transient", transient)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database=database,
        settings=SimpleNamespace(llm_daily_request_limit=100), gateway=SimpleNamespace(available=True))))
    def run(start=True):
        return simulation_router.simulation(request, uuid4(), simulation_router.SimulationRequest(message_id=uuid4(), start=start), {"id": str(uuid4()), "role": "member"})
    return run, stored, library, transient, db, request


def test_library_reuse_does_not_call_provider_or_consume_generation_quota(monkeypatch):
    source = dict(resource_id=str(uuid4()), version=2, topic_id=str(uuid4()), subtopic_id=None, revision=2)
    media = dict(status="resource", title="Gravity", version=2, resource_id=source["resource_id"], html_document="<html><head></head><body>Gravity</body></html>")
    run, stored, library, transient, db, request = route_fixture(monkeypatch, media=(media, source))
    request.app.state.gateway.available = False
    assert json.loads(run().body) == media
    assert stored.result["simulation_source"]["resource_id"] == source["resource_id"]
    transient.run.assert_not_called()


def test_followup_resolved_question_reaches_catalogue_and_generation(monkeypatch):
    plan = decide_response_visual("create interactivity", history=[history_turn("Explain gravity")])
    run, stored, library, transient, db, request = route_fixture(monkeypatch, "create interactivity", saved={"visual_routing": plan})
    generated = MagicMock(return_value={"source": "fixture"})
    monkeypatch.setattr(simulation_router, "generate", generated)
    transient.run.side_effect = lambda owner, message, factory, **kw: {"status": "ready", **factory()}
    run()
    assert library.call_args.args[2] == plan["simulation_question"]
    assert "Explain gravity" in generated.call_args.args[2]
    assert generated.call_args.args[1] == "matter"


def test_plain_science_and_saved_text_do_not_even_retrieve_library(monkeypatch):
    run, stored, library, transient, *_ = route_fixture(monkeypatch, "Explain gravity")
    assert json.loads(run().body)["status"] == "ineligible"
    library.assert_not_called()
    transient.run.assert_not_called()


def test_missing_media_generates_with_context_outside_transaction_and_never_rearms_history(monkeypatch):
    run, stored, library, transient, db, _ = route_fixture(monkeypatch)
    def generate(gateway, engine, question, **kw):
        assert db.begin.return_value.__exit__.called
        assert engine == "matter" and "Selected learning topic" in question and "Falling objects" in question
        return {"engine": engine, "source": "fixture"}
    monkeypatch.setattr(simulation_router, "generate", generate)
    transient.run.side_effect = lambda owner, message, factory, **kw: {"status": "ready", **factory()}
    assert json.loads(run(start=True).body)["engine"] == "matter"
    assert transient.run.call_args.kwargs["start"] is True
    assert transient.run.call_args.kwargs["limit"] == 20
    transient.arm.assert_not_called()


def test_history_retrieval_cannot_start_generation_when_no_job_exists(monkeypatch):
    from app.modules.application.teaching.simulations import TransientSimulations
    run, *_ = route_fixture(monkeypatch)
    monkeypatch.setattr(simulation_router, "transient", TransientSimulations(require_arm=True))
    monkeypatch.setattr(simulation_router, "generate", lambda *a, **kw: pytest.fail("History started a provider call"))
    assert json.loads(run(start=False).body)["status"] == "expired"


def test_delivery_rechecks_publication_version_path_and_suitability(monkeypatch):
    selected = candidate(languages=["en"], grade_min=0, grade_max=3)
    path = dict(curriculum_revision=2, grade="Grade 2")
    monkeypatch.setattr(resource_simulations, "describe_browse_path", lambda *a: path)
    monkeypatch.setattr(resource_simulations, "eligible_candidates", lambda *a: [selected])
    monkeypatch.setattr(resource_simulations, "ResourceStorage", lambda *a: None)
    reader = MagicMock(return_value={"html_document": "isolated HTML"})
    monkeypatch.setattr(resource_simulations, "interactive_data", reader)
    db = MagicMock()
    kwargs = dict(topic_id=uuid4(), subtopic_id=None, revision=2, version=2, language="en")
    assert resource_simulations.open_simulation(db, None, selected.id, **kwargs)["status"] == "resource"
    for changed, status in [(dict(version=1), 409), (dict(revision=1), 409), (dict(language="ta"), 404)]:
        reader.reset_mock()
        with pytest.raises(HTTPException) as error:
            resource_simulations.open_simulation(db, None, selected.id, **(kwargs | changed))
        assert error.value.status_code == status
        reader.assert_not_called()
    monkeypatch.setattr(resource_simulations, "eligible_candidates", lambda *a: [])
    with pytest.raises(HTTPException):
        resource_simulations.open_simulation(db, None, selected.id, **kwargs)


def test_saved_library_choice_is_revalidated_without_reranking(monkeypatch):
    source = dict(resource_id=str(uuid4()), topic_id=str(uuid4()), subtopic_id=None, revision=2, version=2)
    delivery = MagicMock(return_value={"status": "resource"})
    monkeypatch.setattr(visual_media, "open_simulation", delivery)
    monkeypatch.setattr(visual_media, "eligible_candidates", lambda *a: pytest.fail("Saved selection was reranked"))
    result, saved = visual_media.library_simulation(None, None, "Show gravity", saved_source=source)
    assert saved is source and result["status"] == "resource"
    assert delivery.call_args.kwargs["version"] == 2


def test_withdrawn_saved_media_never_falls_back_to_a_paid_generation(monkeypatch):
    route = decide_response_visual("Show gravity", mode="study", context_names=SCIENCE)
    run, stored, library, transient, *_ = route_fixture(monkeypatch, saved={"visual_routing": route, "simulation_source": {"kind": "resource"}})
    library.side_effect = HTTPException(404, "interactive_document_unavailable")
    with pytest.raises(HTTPException):
        run()
    transient.run.assert_not_called()


def test_saved_media_path_cannot_escape_current_study_context(monkeypatch):
    context = TeachingContext({"topic_id": uuid4(), "subtopic_id": None}, SCIENCE, 2, None, None)
    source = dict(resource_id=str(uuid4()), topic_id=str(uuid4()), subtopic_id=None, revision=2, version=2)
    reader = MagicMock()
    monkeypatch.setattr(visual_media, "open_simulation", reader)
    with pytest.raises(HTTPException) as error:
        visual_media.library_simulation(None, None, "Show gravity", context=context, saved_source=source)
    assert error.value.status_code == 409
    reader.assert_not_called()


def test_text_policy_suppresses_automatic_media_without_hiding_a_requested_tutor(monkeypatch):
    from app.modules.application.recommendations import service
    image = candidate(type="image", card={"id": "image"})
    tutor = candidate(kind="tutor", type="tutor", card={"id": "tutor", "name": "Science teacher"})
    def choice(row):
        return dict(candidate_id=str(row.id), candidate_kind=row.kind, candidate_type=row.type, version=row.version,
                    display_mode="optional card", availability_state="available")
    saved = SimpleNamespace(image_decision={"recommendation_decision": {"primary": choice(image), "alternative": choice(tutor)}})
    context = SimpleNamespace(visual_routing={"allow_media_recommendations": False}, earlier_message_ids=[])
    monkeypatch.setattr(service, "load_answer", lambda *a: context)
    monkeypatch.setattr(service, "eligible", lambda *a: ({}, [image, tutor]))
    repository = MagicMock()
    repository.get.return_value = saved
    repository.earlier.return_value = []
    monkeypatch.setattr(service, "RecommendationRepository", lambda *a: repository)
    result = service.recommend(None, None, uuid4(), uuid4(), uuid4())
    assert result["resources"] == [] and result["teachers"][0]["name"] == "Science teacher"


def test_answer_replay_does_not_expose_followup_source_or_call_a_provider(monkeypatch):
    from app.modules.application.teaching import answer_service
    answer = {"status": "ok", "message_id": str(uuid4()), "blocks": [{"kind": "markdown", "text": "Gravity pulls."}]}
    claimed = SimpleNamespace(status="completed", result={**answer, "simulation_source": {"kind": "resource", "resource_id": str(uuid4())}})
    monkeypatch.setattr(answer_service, "claim", lambda *a: claimed)
    database, gateway = MagicMock(), MagicMock()
    body = SimpleNamespace(question="Explain gravity", model_dump=lambda **kw: {"question": "Explain gravity"})
    assert answer_service.ask(database, gateway, uuid4(), uuid4(), "same-key", body) == answer
    gateway.generate.assert_not_called()


def test_library_coordinator_matches_current_topic_before_opening(monkeypatch):
    topic, subtopic = uuid4(), uuid4()
    context = TeachingContext({"topic_id": topic, "subtopic_id": subtopic}, SCIENCE, 2, None, None)
    path = dict(topic_id=topic, subtopic_id=subtopic, curriculum_revision=2, grade="Grade 2", topic_name="Gravity", subtopic_name="Falling objects")
    gravity = candidate()
    unrelated = candidate("Evaporation", description="Water becomes gas")
    monkeypatch.setattr(visual_media, "describe_browse_path", lambda *a: path)
    monkeypatch.setattr(visual_media, "eligible_candidates", lambda *a: [unrelated, gravity])
    opener = MagicMock(return_value={"status": "resource"})
    monkeypatch.setattr(visual_media, "open_simulation", opener)
    media, source = visual_media.library_simulation(None, None, "Showme", context=context)
    assert source["resource_id"] == str(gravity.id) and source["revision"] == 2
    assert media["status"] == "resource" and opener.call_args.kwargs["subtopic_id"] == subtopic
