"""Rollback-only B7 request, replay, and topic binding checks."""
import os
from time import monotonic, sleep
from uuid import UUID, uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.main import create_app
from app.modules.identity.dependencies import require_admin, require_member
from app.modules.identity.models import StudentProfile
from app.modules.conversations.models import AnswerRequest, Message
from app.modules.teaching.gateway import Generated, UnconfiguredGateway

pytestmark = pytest.mark.db_integration


class StubGateway:
    available = True
    def __init__(self):
        self.calls = 0
        self.text = "Gravity pulls objects toward Earth."
        self.last_messages = []
    def generate(self, messages):
        self.calls += 1
        self.last_messages = messages
        assert messages[-1]["role"] == "user"
        return Generated(self.text, "stub-v1", 30, 8)


def test_ask_replay_and_open_curiosity():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for database checks")
    settings = Settings()
    app = create_app(Settings(_env_file=None, environment="test", database_url=settings.database_url))
    member = uuid4()
    app.dependency_overrides[require_member] = lambda: {"id": str(member), "role": "member"}
    app.dependency_overrides[require_admin] = lambda: {"id": str(member), "role": "admin"}
    with TestClient(app) as client:
        gateway = StubGateway()
        app.state.gateway = gateway
        with app.state.database.engine.connect() as connection:
            outer = connection.begin()
            original = app.state.database.sessions
            app.state.database.sessions = sessionmaker(bind=connection, expire_on_commit=False,
                                                        join_transaction_mode="create_savepoint")
            try:
                with app.state.database.session() as db, db.begin():
                    db.add(StudentProfile(id=member, auth_subject=str(member)))
                created = client.post("/api/v1/admin/curricula", json={
                    "code": "b7-" + uuid4().hex[:12], "name": "B7 curriculum"})
                assert created.status_code == 201, created.text
                curriculum = created.json()["id"]
                def child(kind, parent, name):
                    response = client.post("/api/v1/admin/curriculum/" + kind,
                                           json={"parent_id": parent, "name": name})
                    assert response.status_code == 201, response.text
                    return response.json()["id"]
                level = child("level", curriculum, "Level II")
                subject = child("subject", level, "Science")
                domain = child("domain", subject, "Motion")
                topic = child("topic", domain, "Gravity")
                subtopic = child("subtopic", topic, "Falling")
                tree = client.get(f"/api/v1/admin/curricula/{curriculum}/tree").json()
                version = tree["version"]
                assert client.post(f"/api/v1/admin/curriculum/curriculum/{curriculum}/publish",
                    json={"expected_version": version, "expected_draft_revision": tree["draft_revision"]}).status_code == 200
                path = {"curriculum_id": curriculum, "level_id": level, "subject_id": subject,
                        "domain_id": domain, "category_id": None, "topic_id": topic,
                        "subtopic_id": subtopic}
                study = client.post("/api/v1/sessions", json={"mode": "study", "context": path})
                assert study.status_code == 201, study.text
                sid = study.json()["id"]
                body = {"mode": "study", "context": path, "question": "Why does a ball fall?"}
                route = f"/api/v1/sessions/{sid}/ask"
                first = client.post(route, json=body, headers={"Idempotency-Key": "b7-first"})
                assert first.status_code == 200, first.text
                assert first.json()["route"] == "direct_llm"
                assert first.json()["blocks"][0]["text"] == "Gravity pulls objects toward Earth."
                assert gateway.calls == 1
                replay = client.post(route, json=body, headers={"Idempotency-Key": "b7-first"})
                assert replay.json() == first.json() and gateway.calls == 1
                history = client.get(f"/api/v1/sessions/{sid}/messages").json()['items']
                assert next(row for row in history if row['role'] == 'assistant')['request_id'] == first.json()['request_id']
                assert next(row for row in history if row['role'] == 'user')['request_id'] is None
                changed = client.post(route, json={**body, "question": "Changed"},
                                      headers={"Idempotency-Key": "b7-first"})
                assert changed.status_code == 409
                app.state.settings.llm_daily_request_limit = 1
                limited = client.post(route, json={**body, "question": "Another question"},
                                      headers={"Idempotency-Key": "b7-second"})
                assert limited.status_code == 429
                assert limited.json()["error"]["code"] == "daily_limit_reached"
                assert gateway.calls == 1
                app.state.settings.llm_daily_request_limit = 20
                app.state.gateway = UnconfiguredGateway()
                unsupported_body = {**body, "question": "Grade my answer to this test."}
                unsupported = client.post(route, json=unsupported_body,
                    headers={"Idempotency-Key": "b8-unsupported"})
                assert unsupported.status_code == 200, unsupported.text
                assert unsupported.json()["status"] == "unsupported"
                assert unsupported.json()["code"] == "official_grading_unavailable"
                repeated = client.post(route, json=unsupported_body,
                    headers={"Idempotency-Key": "b8-unsupported"})
                assert repeated.json() == unsupported.json() and gateway.calls == 1
                app.state.gateway = gateway
                class EmptyGateway:
                    available = True
                    calls = 0
                    def generate(self, messages):
                        self.calls += 1
                        return Generated(" ", "stub-v1", 20, 0)
                bad_gateway = EmptyGateway()
                app.state.gateway = bad_gateway
                malformed = client.post(route, json={**body, "question": "Another falling question"},
                    headers={"Idempotency-Key": "b8-malformed"})
                assert malformed.status_code == 503
                assert malformed.json()["error"]["code"] == "invalid_provider_output"
                repeated_bad = client.post(route, json={**body, "question": "Another falling question"},
                    headers={"Idempotency-Key": "b8-malformed"})
                assert repeated_bad.status_code == 503 and bad_gateway.calls == 1
                app.state.gateway = gateway
                with app.state.database.session() as db:
                    assert db.query(Message).filter_by(session_id=UUID(sid)).count() == 2
                    answer = db.get(AnswerRequest, UUID(first.json()["request_id"]))
                    assert (answer.prompt_version, answer.profile_version, answer.model) == (
                        "direct-school-3-math1-intent1", "kg5-1", "stub-v1")
                    assert (answer.input_tokens, answer.output_tokens) == (30, 8)
                    assistant = db.query(Message).filter_by(session_id=UUID(sid), role="assistant").one()
                    assert assistant.resolved_subject_id == UUID(subject)
                    assert assistant.resolved_topic_id == UUID(topic)
                curiosity = client.post("/api/v1/sessions", json={"mode": "curiosity"}).json()["id"]
                curiosity_route = f"/api/v1/sessions/{curiosity}/ask"
                capability = client.post(f"/api/v1/sessions/{curiosity}/capability-check",
                    json={"question": "Watch this video and explain it"})
                assert capability.status_code == 200
                assert capability.json()["code"] == "media_understanding_unavailable"
                unsupported_curiosity = client.post(curiosity_route,
                    json={"mode": "curiosity", "question": "Watch this video and explain it"},
                    headers={"Idempotency-Key": "b8-media"})
                assert unsupported_curiosity.status_code == 200
                assert unsupported_curiosity.json()["status"] == "unsupported"
                assert gateway.calls == 1
                open_question = "Explain black holes in simple terms."
                ready = client.post(curiosity_route,
                    json={"mode": "curiosity", "question": open_question},
                    headers={"Idempotency-Key": "b7-curiosity"})
                assert ready.status_code == 200, ready.text
                assert ready.json()["curriculum_version"] is None
                assert gateway.calls == 2
                with app.state.database.session() as db:
                    assistant = db.query(Message).filter_by(session_id=UUID(curiosity), role="assistant").one()
                    assert assistant.resolved_subject_id is None
                    assert assistant.resolved_topic_id is None
                    request = db.get(AnswerRequest, UUID(ready.json()["request_id"]))
                    assert request.prompt_version == "direct-curiosity-open-3-math1"
                old_gate = client.post(curiosity_route,
                    json={"mode": "curiosity", "question": open_question,
                          "topic_check_id": str(uuid4())},
                    headers={"Idempotency-Key": "b7-old-gate"})
                assert old_gate.status_code == 422
                topic_path = {**path, "subtopic_id": None}
                topic_session = client.post("/api/v1/sessions", json={"mode": "study", "context": topic_path})
                assert topic_session.status_code == 201, topic_session.text
                topic_sid = topic_session.json()["id"]
                assert topic_session.json()["context"]["names"]["topic"] == "Gravity"
                assert topic_session.json()["context"]["names"]["subtopic"] is None
                topic_body = {"mode": "study", "context": topic_path, "question": "What is gravity?"}
                topic_route = f"/api/v1/sessions/{topic_sid}/ask"
                topic_answer = client.post(topic_route, json=topic_body,
                    headers={"Idempotency-Key": "b7-topic-question"})
                assert topic_answer.status_code == 200, topic_answer.text
                assert topic_answer.json()["route"] == "direct_llm"
                assert client.post(topic_route, json=topic_body,
                    headers={"Idempotency-Key": "b7-topic-question"}).json() == topic_answer.json()
                assert client.post(topic_route, json={**topic_body, "context": path},
                    headers={"Idempotency-Key": "b7-topic-mismatch"}).status_code == 422
                with app.state.database.session() as db:
                    assert db.query(Message).filter_by(session_id=UUID(topic_sid)).count() == 2
                    topic_assistant = db.query(Message).filter_by(session_id=UUID(topic_sid), role="assistant").one()
                    assert topic_assistant.resolved_topic_id == UUID(topic)
                # F11: actual JSON storage/replay/restoration and follow-up projection.
                import json
                rich_blocks = [{"kind": "markdown", "text": "**Gravity** pulls down. $$d=vt$$"},
                    {"kind": "chart", "chartType": "bar", "title": "Falling distance", "description": "Example data.",
                     "xKey": "seconds", "illustrative": True, "series": [{"key": "metres", "label": "Distance"}],
                     "data": [{"seconds": 1, "metres": 2}, {"seconds": 2, "metres": 4}]}]
                gateway.text = json.dumps({"format": "flame-rich-1", "blocks": rich_blocks})
                for rich_route, rich_body in [(topic_route, topic_body), (curiosity_route, {"mode": "curiosity", "question": "Show a distance chart"})]:
                    response = client.post(rich_route, json=rich_body, headers={"Idempotency-Key": "f11-rich"})
                    assert response.status_code == 200, response.text
                    result = response.json()
                    assert [block["kind"] for block in result["blocks"]] == ["markdown", "chart"]
                    calls = gateway.calls
                    assert client.post(rich_route, json=rich_body, headers={"Idempotency-Key": "f11-rich"}).json() == result
                    assert gateway.calls == calls
                    session_id = rich_route.split("/")[-2]
                    history = client.get(f"/api/v1/sessions/{session_id}/messages").json()["items"]
                    assert next(row for row in history if row["id"] == result["message_id"])["blocks"] == result["blocks"]
                    gateway.text = "The example distance increases."
                    followup = client.post(rich_route, json={**rich_body, "question": "Explain that chart"}, headers={"Idempotency-Key": "f11-followup"})
                    assert followup.status_code == 200, followup.text
                    assert any("Falling distance" in m["content"] for m in gateway.last_messages if m["role"] == "assistant")
                    gateway.text = json.dumps({"format": "flame-rich-1", "blocks": rich_blocks})
                gateway.text = '{"format":"flame-rich-1","blocks":[{"kind":"chart"}]}'
                with app.state.database.session() as db:
                    before = db.query(Message).count()
                failed = client.post(curiosity_route, json={"mode": "curiosity", "question": "Invalid chart"}, headers={"Idempotency-Key": "f11-invalid"})
                assert failed.status_code == 503
                calls = gateway.calls
                replayed_failure = client.post(curiosity_route, json={"mode": "curiosity", "question": "Invalid chart"}, headers={"Idempotency-Key": "f11-invalid"})
                assert replayed_failure.status_code == failed.status_code
                assert replayed_failure.json()["error"] == failed.json()["error"]
                assert gateway.calls == calls
                with app.state.database.session() as db:
                    assert db.query(Message).count() == before
                # F12: trusted activities and server-owned routing survive storage and replay.
                from app.modules.teaching.math_visuals import TEMPLATES
                for math_route, math_body in [(topic_route,{**topic_body,"question":"Explain 3/4 with a fraction bar"}),
                                              (curiosity_route,{"mode":"curiosity","question":"Explain 3/4 with a fraction bar"})]:
                    visual={"kind":"math_visual","version":1,"template":"fraction_bar","title":"Three quarters",
                            "description":"Change the shaded parts.","parameters":{"numerator":3,"denominator":4}}
                    gateway.text=json.dumps({"format":"flame-rich-1","blocks":[{"kind":"markdown","text":"Three of four equal parts are shaded."},visual]})
                    response=client.post(math_route,json=math_body,headers={"Idempotency-Key":"f12-fraction"})
                    assert response.status_code == 200, response.text
                    answer=response.json()
                    assert answer["blocks"][1]["template"] == "fraction_bar"
                    assert answer["rendering_decision"]["preferred_template"] == "fraction_bar"
                    assert answer["rendering_decision"]["selected_engines"] == ["konva"]
                    calls=gateway.calls
                    assert client.post(math_route,json=math_body,headers={"Idempotency-Key":"f12-fraction"}).json() == answer
                    assert gateway.calls == calls
                    session_id=math_route.split("/")[-2]
                    saved=client.get(f"/api/v1/sessions/{session_id}/messages").json()["items"]
                    assert next(row for row in saved if row["id"]==answer["message_id"])["blocks"] == answer["blocks"]
                    gateway.text="The shaded parts are three quarters of the whole."
                    follow=client.post(math_route,json={**math_body,"question":"Explain that activity"},headers={"Idempotency-Key":"f12-followup"})
                    assert follow.status_code == 200, follow.text
                    assert any("Saved initial activity: fraction_bar" in m["content"] for m in gateway.last_messages if m["role"]=="assistant")
                # F13: fresh owned answers grant one transient generation, never source persistence.
                gateway.text = "Gravity accelerates a falling ball."
                simulation_body = {"mode": "curiosity", "question": "Interactive falling ball with adjustable gravity"}
                simulation_answer = client.post(curiosity_route, json=simulation_body, headers={"Idempotency-Key": "f13-answer"})
                assert simulation_answer.status_code == 200, simulation_answer.text
                message_id = simulation_answer.json()["message_id"]
                simulation_route = f"/api/v1/sessions/{curiosity}/simulation"
                payload = {"message_id": message_id}
                assert client.post(simulation_route, json=payload).json()["status"] == "expired"
                private_source = "export default api=>{api.matterWorld();return {}};/*F13_PRIVATE_SOURCE*/"
                gateway.text = json.dumps({"version": 1, "title": "Falling ball", "description": "Adjust gravity", "source": private_source})
                generated = client.post(simulation_route, json={**payload, "start": True})
                deadline = monotonic() + 3
                while generated.json().get("status") == "pending" and monotonic() < deadline:
                    sleep(.01)
                    generated = client.post(simulation_route, json={**payload, "start": False})
                assert generated.status_code == 200, generated.text
                assert generated.json()["source"] == private_source and generated.json()["engine"] == "matter"
                assert generated.headers["cache-control"] == "no-store"
                calls = gateway.calls
                assert client.post(simulation_route, json={**payload, "start": True}).json() == generated.json()
                assert gateway.calls == calls
                with app.state.database.session() as db:
                    assert all("F13_PRIVATE_SOURCE" not in json.dumps(row.blocks) for row in db.query(Message).all())
                    assert all("F13_PRIVATE_SOURCE" not in json.dumps(row.result) for row in db.query(AnswerRequest).all())
                original_member = app.dependency_overrides[require_member]
                app.dependency_overrides[require_member] = lambda: {"id": str(uuid4()), "role": "member"}
                assert client.post(simulation_route, json={**payload, "start": True}).status_code == 404
                app.dependency_overrides[require_member] = original_member
                from app.modules.teaching.simulations import transient
                transient.entries[(str(member), message_id)].expires = 0
                assert client.post(simulation_route, json={**payload, "start": True}).json()["status"] == "expired"
                assert gateway.calls == calls
                # Streaming shares final validation/persistence and exact-key replay.
                gateway.text = "Gravity pulls objects downward."
                def stream(messages, callback):
                    callback(gateway.text)
                    return gateway.generate(messages)
                gateway.generate_stream = stream
                streamed = client.post(curiosity_route + "-stream", json={"mode": "curiosity", "question": "Explain gravity simply"}, headers={"Idempotency-Key": "f13-stream"})
                assert streamed.status_code == 200, streamed.text
                events = [json.loads(line) for line in streamed.text.splitlines()]
                assert any(event["type"] == "delta" for event in events)
                assert events[-1]["type"] == "answer" and events[-1]["answer"]["status"] == "ok"
                calls = gateway.calls
                replay_stream = client.post(curiosity_route + "-stream", json={"mode": "curiosity", "question": "Explain gravity simply"}, headers={"Idempotency-Key": "f13-stream"})
                assert json.loads(replay_stream.text.splitlines()[-1])["answer"] == events[-1]["answer"]
                assert gateway.calls == calls
                gateway.text = "https://example.test/fabricated-proof"
                unsafe_stream = client.post(curiosity_route + "-stream", json={"mode": "curiosity", "question": "Explain gravity simply"}, headers={"Idempotency-Key": "f13-stream-policy"})
                unsafe_events = [json.loads(line) for line in unsafe_stream.text.splitlines()]
                assert not any(event["type"] == "delta" for event in unsafe_events)
                assert unsafe_events[-1]["answer"]["status"] == "error"
                assert unsafe_events[-1]["answer"]["code"] == "invalid_provider_output"
                # A selected output language augments trusted policy without rewriting the question.
                app.state.settings.llm_daily_request_limit = 100
                gateway.text = "ஈர்ப்பு விசை பொருள்களை கீழே இழுக்கிறது."
                language_body = {"mode": "curiosity", "question": "Explain gravity in English", "response_language": "ta"}
                translated = client.post(curiosity_route, json=language_body, headers={"Idempotency-Key": "answer-language-ta"})
                assert translated.status_code == 200, translated.text
                assert "Tamil" in gateway.last_messages[0]["content"]
                assert gateway.last_messages[-1]["content"] == language_body["question"]
                calls = gateway.calls
                assert client.post(curiosity_route, json=language_body, headers={"Idempotency-Key": "answer-language-ta"}).json() == translated.json()
                assert gateway.calls == calls
                changed_language = client.post(curiosity_route, json={**language_body, "response_language": "hi"}, headers={"Idempotency-Key": "answer-language-ta"})
                assert changed_language.status_code == 409
                with app.state.database.session() as db:
                    latest_question = db.query(Message).filter_by(session_id=UUID(curiosity), role="user").order_by(Message.turn_number.desc()).first()
                    assert latest_question.blocks == [{"kind": "text", "text": language_body["question"]}]
            finally:
                app.state.database.sessions = original
                outer.rollback()
