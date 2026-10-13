"""Rollback-only B7 request, replay, and topic binding checks."""
import os
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
    def generate(self, messages):
        self.calls += 1
        assert messages[-1]["role"] == "user"
        return Generated("Gravity pulls objects toward Earth.", "stub-v1", 30, 8)


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
                        "direct-school-1-intent1", "kg5-1", "stub-v1")
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
                    assert request.prompt_version == "direct-curiosity-open-1"
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
            finally:
                app.state.database.sessions = original
                outer.rollback()
