"""Rollback-only B6 database boundary checks."""
import os
from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.modules.conversations.models import PendingClarification
from app.modules.teaching.models import TopicCheckEvent
from app.modules.identity.dependencies import require_admin, require_member
from app.modules.identity.models import StudentProfile
from app.modules.teaching.clarification import create_pending, continue_pending
from app.modules.teaching.service import prepare

pytestmark = pytest.mark.db_integration


def test_owned_resolution_clarification_and_revision():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for database checks")
    settings = Settings()
    app = create_app(Settings(_env_file=None, environment="test", database_url=settings.database_url))
    student, stranger = uuid4(), uuid4()
    app.dependency_overrides[require_member] = lambda: {"id": str(student), "role": "member"}
    app.dependency_overrides[require_admin] = lambda: {"id": str(student), "role": "admin"}
    with TestClient(app) as client:
        with app.state.database.engine.connect() as connection:
            outer = connection.begin()
            original = app.state.database.sessions
            app.state.database.sessions = sessionmaker(bind=connection, expire_on_commit=False,
                                                         join_transaction_mode="create_savepoint")
            try:
                with app.state.database.session() as db, db.begin():
                    db.add_all([StudentProfile(id=student, auth_subject=str(student)),
                                StudentProfile(id=stranger, auth_subject=str(stranger))])
                created = client.post("/api/v1/admin/curricula", json={
                    "code": "b6-" + uuid4().hex[:12], "name": "B6 programme"})
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
                falling = child("subtopic", topic, "Falling")
                orbit = child("subtopic", topic, "Orbit")
                version = client.get(f"/api/v1/admin/curricula/{curriculum}/tree").json()["version"]
                published = client.post(f"/api/v1/admin/curriculum/curriculum/{curriculum}/publish",
                                        json={"expected_version": version})
                assert published.status_code == 200, published.text
                study_path = {"curriculum_id": curriculum, "level_id": level, "subject_id": subject,
                              "domain_id": domain, "category_id": None, "topic_id": topic,
                              "subtopic_id": falling}
                study = client.post("/api/v1/sessions", json={"mode": "study", "context": study_path})
                curiosity = client.post("/api/v1/sessions", json={"mode": "curiosity"})
                assert study.status_code == curiosity.status_code == 201
                study_id, curiosity_id = UUID(study.json()["id"]), UUID(curiosity.json()["id"])
                def check(session_id, question, key):
                    return client.post(f"/api/v1/sessions/{session_id}/topic-check",
                                       json={"question": question}, headers={"Idempotency-Key": key})
                study_gate = check(study_id, "Why does it fall?", "b6-study-1")
                assert study_gate.status_code == 200, study_gate.text
                assert study_gate.json()["status"] == "ready"
                assert study_gate.json()["answer_available"] is True
                scope = check(curiosity_id, "Explain black holes", "b6-scope-1")
                assert scope.status_code == 200
                assert scope.json()["status"] == "out_of_scope"
                gate = check(curiosity_id, "Explain gravity", "b6-clarify-1")
                assert gate.status_code == 200, gate.text
                assert gate.json()["status"] == "clarification"
                assert len(gate.json()["candidates"]) == 2
                current = client.get(f"/api/v1/sessions/{curiosity_id}/topic-check")
                assert current.status_code == 200
                assert current.json()["pending"]["clarification_id"] == gate.json()["clarification_id"]
                assert current.json()["pending"]["request_id"] == gate.json()["request_id"]
                chosen = client.post(
                    f"/api/v1/sessions/{curiosity_id}/clarifications/{gate.json()['clarification_id']}",
                    json={"clarification_id": gate.json()["clarification_id"],
                          "reply": "the second one"})
                assert chosen.status_code == 200, chosen.text
                assert chosen.json()["status"] == "ready"
                assert chosen.json()["question"] == "Explain gravity"
                assert client.get(f"/api/v1/sessions/{curiosity_id}/topic-check").json()["pending"] is None
                assert check(curiosity_id, "Explain gravity", "b6-clarify-1").json() == chosen.json()
                assert check(curiosity_id, "Different question", "b6-clarify-1").status_code == 409
                repeated_choice = client.post(
                    f"/api/v1/sessions/{curiosity_id}/clarifications/{gate.json()['clarification_id']}",
                    json={"clarification_id": gate.json()["clarification_id"],
                          "reply": "the second one"})
                assert repeated_choice.status_code == 200
                changed_choice = client.post(
                    f"/api/v1/sessions/{curiosity_id}/clarifications/{gate.json()['clarification_id']}",
                    json={"clarification_id": gate.json()["clarification_id"],
                          "subtopic_id": falling})
                assert changed_choice.status_code == 409
                page = client.get(f"/api/v1/sessions/{curiosity_id}/topic-check/history?limit=1")
                assert page.status_code == 200, page.text
                assert page.json()["items"][0]["status"] == "ready"
                assert page.json()["next_cursor"]
                older_page = client.get(f"/api/v1/sessions/{curiosity_id}/topic-check/history",
                                        params={"cursor": page.json()["next_cursor"], "limit": 1})
                assert older_page.json()["items"][0]["status"] == "out_of_scope"
                with app.state.database.session() as db:
                    event = db.get(TopicCheckEvent, UUID(gate.json()["request_id"]))
                    assert event.context_snapshot["subject_id"] == subject
                    assert event.context_snapshot["topic_id"] == topic
                    assert event.context_snapshot["revision"] >= 1
                replacement = check(curiosity_id, "Explain gravity", "b6-clarify-2").json()
                assert replacement["status"] == "clarification"
                check(curiosity_id, "Explain black holes", "b6-scope-2")
                assert client.post(
                    f"/api/v1/sessions/{curiosity_id}/clarifications/{replacement['clarification_id']}",
                    json={"clarification_id": replacement["clarification_id"],
                          "subtopic_id": falling}).status_code == 409
                assert check(curiosity_id, "Explain gravity", "b6-clarify-2").json()["status"] == "cancelled"
                expiring = check(curiosity_id, "Explain gravity", "b6-expiry-1").json()
                assert expiring["status"] == "clarification"
                with app.state.database.session() as db, db.begin():
                    pending_row = db.get(PendingClarification, UUID(expiring["clarification_id"]))
                    pending_row.expires_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
                expired_choice = client.post(
                    f"/api/v1/sessions/{curiosity_id}/clarifications/{expiring['clarification_id']}",
                    json={"clarification_id": expiring["clarification_id"], "reply": "first"})
                assert expired_choice.status_code == 409
                assert expired_choice.json()["error"]["code"] == "clarification_expired"
                assert client.get(f"/api/v1/sessions/{curiosity_id}/topic-check").json()["pending"] is None
                expired_history = client.get(f"/api/v1/sessions/{curiosity_id}/topic-check/history?limit=1").json()
                assert expired_history["items"][0]["status"] == "expired"
                assert "topic again" in expired_history["items"][0]["response"]["message"]
                app.dependency_overrides[require_member] = lambda: {"id": str(stranger), "role": "member"}
                assert client.get(f"/api/v1/sessions/{curiosity_id}/topic-check/history").status_code == 404
                assert check(curiosity_id, "Explain gravity", "stranger-key").status_code == 404
                app.dependency_overrides[require_member] = lambda: {"id": str(student), "role": "member"}
                with app.state.database.session() as db, db.begin():
                    ready = prepare(db, student, study_id, "Why does it fall?")
                    assert ready.status == "ready"
                    assert ready.context.ids["subtopic_id"] == UUID(falling)
                    assert ready.prompt.profile_version == "kg5-1"
                    ambiguous = prepare(db, student, curiosity_id, "Explain gravity")
                    assert ambiguous.status == "clarification"
                    assert {item.ids["subtopic_id"] for item in ambiguous.candidates} == {UUID(falling), UUID(orbit)}
                    pending = create_pending(db, student, curiosity_id, "Explain gravity",
                                             __import__("app.modules.teaching.resolution", fromlist=["Resolution"]).Resolution(
                                                 "clarification", None, ambiguous.candidates))
                    pending_id = pending.id
                with app.state.database.session() as db, db.begin():
                    continuation = continue_pending(db, student, curiosity_id, pending_id,
                                                    subtopic_id=UUID(falling))
                    assert continuation.question == "Explain gravity"
                    assert continuation.context.ids["subject_id"] == UUID(subject)
                    replay = continue_pending(db, student, curiosity_id, pending_id,
                                               subtopic_id=UUID(falling))
                    assert replay.context.ids == continuation.context.ids
                    with pytest.raises(HTTPException) as private:
                        continue_pending(db, stranger, curiosity_id, pending_id,
                                         subtopic_id=UUID(falling))
                    assert private.value.status_code == 404
                renamed = client.patch(f"/api/v1/admin/curriculum/topic/{topic}",
                                       json={"expected_version": 1, "name": "Gravity updated"})
                assert renamed.status_code == 200, renamed.text
                with app.state.database.session() as db:
                    with pytest.raises(HTTPException) as stale:
                        prepare(db, student, study_id, "Again?")
                    assert stale.value.detail == "unavailable_context"
                assert client.request("DELETE", f"/api/v1/sessions/{curiosity_id}", json={"confirm": True}).status_code == 200
                with app.state.database.session() as db:
                    assert db.get(PendingClarification, pending_id) is None
                    assert db.get(TopicCheckEvent, UUID(gate.json()["request_id"])) is None
            finally:
                app.state.database.sessions = original
                outer.rollback()






