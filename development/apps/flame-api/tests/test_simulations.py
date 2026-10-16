from concurrent.futures import ThreadPoolExecutor
from time import sleep
from types import SimpleNamespace
import json
import pytest
from app.modules.application.teaching.simulations import select_engine, generate, TransientSimulations
from app.modules.application.teaching.gateway import GatewayError, OpenAIResponsesGateway
import httpx


@pytest.mark.parametrize("question,engine", [
    ("Explain gravity", None), ("Explain fractions using a chart", None),
    ("Interactive falling ball with gravity", "matter"),
    ("Two draggable balls colliding using Matter.js", "matter"),
    ("Rotatable 3D solar system", "three"), ("Interactive Three.js molecule", "three"),
    ("Phaser interactive game", "phaser"), ("Rive animation", "rive"),
    ("HTML5 animation", "html5"), ("Text only, no simulation of gravity", None),
    ("Interactive fraction bar", None), ("Show an interactive coordinate graph", None),
    ("using matter.js create a force explainer", "matter"),
    ("using three.js show me the world", "three"),
    ("Build a solar system using React Three Fiber", "r3f"),
    ("Show a learning activity using Phaser", "phaser"),
    ("Show the weather using Rive", "rive"),
    ("Draw a bouncing ball using HTML5 Canvas", "html5"),
    ("What is Matter.js?", None), ("Explain the Three.js library", None),
    ("Explain how to create a Three.js scene, text only", None),
    ("Using Matter.js create a force explainer, no simulation", None),
    ("Show fractions", None), ("Create a coordinate graph", None),
])
def test_engine_selection(question, engine):
    assert select_engine(question) == engine


@pytest.mark.parametrize("question", [
    "using matter.js create a force explainer",
    "using three.js show me the world",
])
def test_explicit_visual_requests_receive_sandbox_prompt_including_after_old_refusal(question):
    from app.modules.application.teaching.prompt import assemble_open_curiosity
    prompt = assemble_open_curiosity(question, [{
        "user": [{"kind": "text", "text": question}],
        "assistant": [{"kind": "text", "text": "I cannot run an interactive simulation here."}],
    }])
    assert prompt.version.endswith("-sim1")
    assert "separate sandbox" in prompt.messages[0]["content"]
    assert "Do not claim the simulation has already run or refuse" in prompt.messages[0]["content"]


def test_generated_contract_and_failure():
    data = {"version": 1, "title": "Gravity", "description": "Explore", "source": "export default ()=>({})"}
    class Gateway:
        def generate(self, messages):
            assert "Selected engine: matter" in messages[-1]["content"]
            return SimpleNamespace(text=json.dumps(data))
    assert generate(Gateway(), "matter", "Falling ball")["engine"] == "matter"
    data["unexpected"] = True
    with pytest.raises(GatewayError):
        generate(Gateway(), "matter", "Falling ball")


def test_source_generation_has_separate_bounded_transport_budget(monkeypatch):
    data = {"version": 1, "title": "Gravity", "description": "Explore", "source": "export default ()=>({})"}
    original = OpenAIResponsesGateway("fixture", "gpt-6-luna", timeout_seconds=12, max_output_tokens=1500)
    def generated(gateway, messages):
        assert gateway is not original
        assert gateway.key == original.key and gateway.model == original.model
        assert gateway.max_output_tokens == original.max_output_tokens == 1500
        assert gateway.timeout_seconds == 60 and gateway.attempts == 1
        assert gateway.reasoning_effort == "low" and original.reasoning_effort is None
        return SimpleNamespace(text=json.dumps(data))
    monkeypatch.setattr(OpenAIResponsesGateway, "generate", generated)
    assert generate(original, "matter", "Create a force explainer")["engine"] == "matter"
    assert original.timeout_seconds == 12


def test_background_jobs_return_pending_deduplicate_and_limit_running_work():
    from threading import Event
    from time import monotonic
    store, entered, release, calls = TransientSimulations(), Event(), Event(), []
    def factory():
        calls.append(1)
        entered.set()
        assert release.wait(2)
        return {"source": "ephemeral"}
    try:
        assert store.run("a", "m", factory, start=True, background=True)["status"] == "pending"
        assert entered.wait(1)
        for _ in range(3):
            assert store.run("a", "m", factory, background=True)["status"] == "pending"
        assert len(calls) == 1
        for i in range(3):
            assert store.run("a", str(i), factory, start=True, background=True)["status"] == "pending"
        assert store.run("a", "overflow", factory, start=True, background=True)["status"] == "limited"
    finally:
        release.set()
    deadline = monotonic() + 2
    result = store.run("a", "m", factory, background=True)
    while result["status"] == "pending" and monotonic() < deadline:
        sleep(.005)
        result = store.run("a", "m", factory, background=True)
    assert result == {"status": "ready", "source": "ephemeral"}


def test_simulation_transport_does_not_retry_timeouts(monkeypatch):
    calls = []
    original = httpx.Client
    def fail(request):
        calls.append(1)
        raise httpx.ReadTimeout("fixture", request=request)
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(fail), **kw))
    with pytest.raises(GatewayError):
        generate(OpenAIResponsesGateway("fixture", "fixture"), "matter", "Create a force explainer")
    assert calls == [1]


def test_source_reasoning_payload_and_incomplete_budget_diagnostics(monkeypatch):
    original = httpx.Client
    def handle(request):
        payload = json.loads(request.content)
        assert payload["reasoning"] == {"effort": "low"}
        assert payload["max_output_tokens"] == 1500 and payload["store"] is False
        return httpx.Response(200, json={"status": "incomplete", "incomplete_details": {"reason": "max_output_tokens"}})
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    with pytest.raises(GatewayError) as error:
        generate(OpenAIResponsesGateway("fixture", "gpt-6-luna"), "matter", "Create a force explainer")
    assert error.value.code == "provider_output_limit"


def test_source_failure_diagnostics_are_sanitized_and_cached(caplog):
    store = TransientSimulations()
    def fail():
        raise GatewayError("provider_unavailable")
    assert store.run("a", "m", fail, start=True) == {"status": "error", "code": "provider_unavailable"}
    assert store.run("a", "m", lambda: pytest.fail("billed twice"), start=True)["code"] == "provider_unavailable"
    def unsafe():
        raise GatewayError("secret-source-must-not-be-logged")
    assert store.run("a", "n", unsafe, start=True)["code"] == "simulation_generation_failed"
    assert "secret-source-must-not-be-logged" not in caplog.text


def test_transient_owner_isolation_dedup_and_no_automatic_regeneration():
    store, calls = TransientSimulations(), []
    def factory():
        calls.append(1)
        sleep(.02)
        return {"source": "private"}
    assert store.run("a", "m", factory) == {"status": "expired"}
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda _: store.run("a", "m", factory, start=True), range(4)))
    assert len(calls) == 1 and all(r["source"] == "private" for r in results)
    assert store.run("b", "m", factory) == {"status": "expired"}
    store.entries[("a", "m")].expires = 0
    assert store.run("a", "m", factory) == {"status": "expired"}
    assert len(calls) == 1


def test_failed_generation_is_deduplicated_and_bounded():
    store = TransientSimulations(maximum=1)
    def fail():
        raise RuntimeError("do not log source")
    assert store.run("a", "m", fail, start=True)["status"] == "error"
    assert store.run("a", "m", lambda: pytest.fail("billed twice"), start=True)["status"] == "error"
    assert store.run("a", "n", fail, start=True)["status"] == "limited"


def test_expired_or_restarted_runtime_cannot_automatically_bill_again():
    store = TransientSimulations(require_arm=True)
    def factory():
        return {"source": "ephemeral"}
    assert store.run("a", "m", factory, start=True)["status"] == "expired"
    store.arm("a", "m")
    assert store.run("a", "m", factory, start=True)["status"] == "ready"
    store.entries[("a", "m")].expires = 0
    assert store.run("a", "m", lambda: pytest.fail("regenerated"), start=True)["status"] == "expired"
    restarted = TransientSimulations(require_arm=True)
    assert restarted.run("a", "m", factory, start=True)["status"] == "expired"


def test_streaming_transport_keeps_final_validation_and_budget(monkeypatch):
    complete = {"status": "completed", "model": "fixture", "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "Hello."}]}], "usage": {"input_tokens": 3, "output_tokens": 2}}
    events = [{"type": "response.output_text.delta", "delta": "Hello."}, {"type": "response.completed", "response": complete}]
    original = httpx.Client
    def handle(request):
        body = json.loads(request.content)
        assert body["stream"] is True and body["store"] is False and body["max_output_tokens"] == 1500
        return httpx.Response(200, text="".join("data: " + json.dumps(e) + "\n\n" for e in events))
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    deltas = []
    gateway = OpenAIResponsesGateway("fixture", "fixture")
    assert gateway.generate_stream([], deltas.append).text == "Hello."
    assert deltas == ["Hello."]
    complete["status"] = "incomplete"
    with pytest.raises(GatewayError):
        gateway.generate_stream([], lambda _: None)


def test_streaming_keeps_spending_limit_failure_distinct(monkeypatch):
    original = httpx.Client
    monkeypatch.setattr(httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(
        lambda _: httpx.Response(429, json={"error": {"code": "project_spend_limit_exceeded"}})), **kw))
    with pytest.raises(GatewayError) as error:
        OpenAIResponsesGateway("fixture", "fixture").generate_stream([], lambda _: pytest.fail("unexpected delta"))
    assert error.value.code == "provider_budget_exceeded"
