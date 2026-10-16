"""Rollback-only B5 session and activity checks."""
import os
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.main import create_app
from app.modules.functional.identity.dependencies import require_admin, require_member
from app.modules.functional.identity.models import StudentProfile, BrowserSession
from app.modules.functional.conversations.models import Message, AnswerRequest
from app.modules.functional.conversations.requests import claim, finalize

pytestmark = pytest.mark.db_integration

def test_sessions_activity_and_deletion():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for database checks")
    settings = Settings()
    app = create_app(Settings(_env_file=None, environment="test", database_url=settings.database_url,
                              supabase_url="https://test.supabase.co",
                              supabase_service_role_key="test-service-key"))
    first, second, admin = uuid4(), uuid4(), uuid4()
    principal = {"id": str(first), "role": "member"}
    app.dependency_overrides[require_member] = lambda: principal
    app.dependency_overrides[require_admin] = lambda: {"id": str(admin), "role": "admin"}
    with TestClient(app) as client:
        with app.state.database.engine.connect() as connection:
            outer = connection.begin()
            original = app.state.database.sessions
            app.state.database.sessions = sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
            try:
                with app.state.database.session() as db, db.begin():
                    db.add_all([StudentProfile(id=first, auth_subject=str(first)),
                                StudentProfile(id=second, auth_subject=str(second)),
                                StudentProfile(id=admin, auth_subject=str(admin))])
                    with app.state.database.session() as db, db.begin():
                        from datetime import datetime, timedelta, timezone
                        db.add(BrowserSession(id_hash="b5-" + first.hex, auth_subject=str(first),
                            access_token=b"encrypted", refresh_token=b"encrypted",
                            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)))
                created = client.post("/api/v1/admin/curricula", json={
                    "code": "b5-" + uuid4().hex[:12], "name": "B5 curriculum"}).json()
                cid = created["id"]
                def child(kind, parent, name):
                    response = client.post("/api/v1/admin/curriculum/" + kind,
                                           json={"parent_id": parent, "name": name})
                    assert response.status_code == 201, response.text
                    return response.json()["id"]
                level = child("level", cid, "Level")
                subject = child("subject", level, "Science")
                domain = child("domain", subject, "Motion")
                topic = child("topic", domain, "Gravity")
                subtopic = child("subtopic", topic, "Falling")
                draft_tree = client.get(f"/api/v1/admin/curricula/{cid}/tree").json()
                assert client.post(f"/api/v1/admin/curriculum/curriculum/{cid}/publish",
                                   json={"expected_version": draft_tree["version"],
                                         "expected_draft_revision": draft_tree["draft_revision"]}).status_code == 200
                path = {"curriculum_id": cid, "level_id": level, "subject_id": subject,
                        "domain_id": domain, "category_id": None, "topic_id": topic,
                        "subtopic_id": subtopic}
                invalid_path = {**path, "subject_id": str(uuid4())}
                assert client.post("/api/v1/sessions", json={"mode": "study",
                                   "context": invalid_path}).status_code == 422
                study = client.post("/api/v1/sessions", json={"mode": "study", "context": path})
                assert study.status_code == 201, study.text
                repeated_study = client.post("/api/v1/sessions", json={"mode": "study", "context": path})
                assert repeated_study.status_code == 201, repeated_study.text
                assert repeated_study.json()["id"] == study.json()["id"]
                pinned_study = client.patch("/api/v1/sessions/" + study.json()["id"] + "/pin", json={"pinned": True})
                assert pinned_study.status_code == 200 and pinned_study.json()["pinned"] is True
                assert study.json()["context"]["names"]["subtopic"] == "Falling"
                assert study.json()["revision"] >= 1
                membership = client.post("/api/v1/me/learning", json={
                    "curriculum_id": cid, "level_id": level, "subject_id": subject}).json()
                hidden = client.patch("/api/v1/me/learning/" + membership["id"],
                                      json={"visible": False, "expected_version": membership["version"]})
                assert hidden.status_code == 200, hidden.text
                assert client.get("/api/v1/sessions/" + study.json()["id"]).status_code == 200
                restored = client.patch("/api/v1/me/learning/" + membership["id"],
                                        json={"visible": True, "expected_version": hidden.json()["version"]})
                assert restored.status_code == 200, restored.text
                assert client.get("/api/v1/sessions/" + study.json()["id"]).status_code == 200
                study_payload = {"mode": "study", "context": path, "question": "Why does it fall?"}
                with app.state.database.session() as db, db.begin():
                    study_claim = claim(db, first, __import__("uuid").UUID(study.json()["id"]),
                                        "study-completed-before-revision", study_payload)
                with app.state.database.session() as db, db.begin():
                    finalize(db, study_claim.request_id, study_claim.token, "Why does it fall?",
                             {"status": "ok", "blocks": [{"kind": "text", "text": "Gravity"}]})
                renamed = client.patch(f"/api/v1/admin/curriculum/topic/{topic}",
                                       json={"expected_version": 1, "name": "Gravity revised"})
                assert renamed.status_code == 200, renamed.text
                assert client.get("/api/v1/sessions/" + study.json()["id"]).json()["context"]["names"]["topic"] == "Gravity"
                with app.state.database.session() as db, db.begin():
                    historical = claim(db, first, __import__("uuid").UUID(study.json()["id"]),
                                       "study-completed-before-revision", study_payload)
                    assert historical.status == "completed"
                    assert historical.result["blocks"][0]["text"] == "Gravity"
                with app.state.database.session() as db, db.begin():
                    from fastapi import HTTPException
                    with pytest.raises(HTTPException) as unavailable:
                        claim(db, first, __import__("uuid").UUID(study.json()["id"]),
                              "study-request-one", {"mode": "study", "context": path,
                                                    "question": "Why does it fall?"})
                    assert unavailable.value.detail == "unavailable_context"
                curiosity = client.post("/api/v1/sessions", json={"mode": "curiosity"})
                assert curiosity.status_code == 201, curiosity.text
                sid = curiosity.json()["id"]
                assert client.post("/api/v1/sessions", json={"mode": "study"}).status_code == 422
                assert client.post("/api/v1/me/activity", json={"event_type": "visit", "deduplication_key": "visit-event-001"}).json()["recorded"]
                assert not client.post("/api/v1/me/activity", json={"event_type": "visit", "deduplication_key": "visit-event-001"}).json()["recorded"]
                with app.state.database.session() as db, db.begin():
                    db.add_all([Message(session_id=__import__("uuid").UUID(sid), turn_number=1, role="user", blocks=[{"kind":"text","text":"why"}]),
                                Message(session_id=__import__("uuid").UUID(sid), turn_number=1, role="assistant", blocks=[{"kind":"text","text":"because"}])])
                bad_cursor = client.get("/api/v1/sessions?cursor=%%%")
                assert bad_cursor.status_code == 422
                assert bad_cursor.json()["error"]["code"] == "invalid_cursor"
                listing = client.get("/api/v1/sessions").json()
                assert listing["items"][0]["id"] == sid
                assert listing["items"][0]["first_question"] == "why"
                assert next(item for item in listing["items"] if item["id"] == study.json()["id"])["pinned"] is True
                assert len(client.get(f"/api/v1/sessions/{sid}/messages").json()["items"]) == 2
                page_one = client.get("/api/v1/sessions?limit=1").json()
                assert page_one["items"][0]["id"] == sid and page_one["next_cursor"]
                page_two = client.get("/api/v1/sessions?limit=1&cursor=" + page_one["next_cursor"]).json()
                assert page_two["items"][0]["id"] == study.json()["id"]
                assert client.post("/api/v1/sessions/recent/clear", json={"confirm": True}).status_code == 200
                cleared_rows = client.get("/api/v1/sessions").json()["items"]
                assert next(row for row in cleared_rows if row["id"] == sid)["recent_at"] is None
                pinned_row = next(row for row in cleared_rows if row["id"] == study.json()["id"])
                assert pinned_row["pinned"] is True and pinned_row["recent_at"] is not None
                assert len(client.get(f"/api/v1/sessions/{sid}/messages").json()["items"]) == 2
                assert client.post(f"/api/v1/sessions/{sid}/recent", json={"confirm": True}).json()["recent_at"]
                assert client.post("/api/v1/sessions/pins/clear", json={"confirm": True}).status_code == 200
                unpinned = client.get("/api/v1/sessions/" + study.json()["id"]).json()
                assert unpinned["pinned"] is False and unpinned["recent_at"] is not None
                assert len(client.get("/api/v1/sessions/" + study.json()["id"] + "/messages").json()["items"]) == 2

                from app.modules.functional.conversations.router import bounded_history
                with app.state.database.session() as db:
                    history = bounded_history(db, first, __import__("uuid").UUID(sid), max_turns=1)
                    assert len(history) == 1 and history[0]["user"][0]["text"] == "why"
                    assert bounded_history(db, first, __import__("uuid").UUID(sid), max_chars=1) == []
                    with pytest.raises(HTTPException) as private_history:
                        bounded_history(db, second, __import__("uuid").UUID(sid))
                    assert private_history.value.status_code == 404
                first_page = client.get(f"/api/v1/sessions/{sid}/messages?limit=1").json()
                assert first_page["items"][0]["role"] == "assistant"
                second_page = client.get(f"/api/v1/sessions/{sid}/messages?limit=1&cursor=" +
                                         first_page["next_cursor"]).json()
                assert second_page["items"][0]["role"] == "user"
                assert second_page["next_cursor"] is None
                assert client.get(f"/api/v1/admin/students/{first}/activity").json()["questions"] == 2
                another = client.post("/api/v1/sessions", json={"mode": "curiosity"}).json()["id"]
                payload = {"mode": "curiosity", "context": None, "question": "Why?"}
                with app.state.database.session() as db, db.begin():
                    first_claim = claim(db, first, __import__("uuid").UUID(another), "request-key-one", payload)
                    assert first_claim.status == "claimed"
                with app.state.database.session() as db, db.begin():
                    from fastapi import HTTPException
                    with pytest.raises(HTTPException) as pending:
                        claim(db, first, __import__("uuid").UUID(another), "request-key-one", payload)
                    assert pending.value.detail == "request_in_progress"
                    with pytest.raises(HTTPException) as different:
                        claim(db, first, __import__("uuid").UUID(another), "request-key-two", payload)
                    assert different.value.detail == "session_request_in_progress"
                with app.state.database.session() as db, db.begin():
                    finalize(db, first_claim.request_id, first_claim.token, "Why?",
                             {"status": "ok", "blocks": [{"kind": "text", "text": "Answer"}]})
                with app.state.database.session() as db, db.begin():
                    replay = claim(db, first, __import__("uuid").UUID(another), "request-key-one", payload)
                    assert replay.status == "completed"
                    with pytest.raises(HTTPException) as changed:
                        claim(db, first, __import__("uuid").UUID(another), "request-key-one",
                              {**payload, "question": "Different"})
                    assert changed.value.detail == "idempotency_key_conflict"
                recovery_id = __import__("uuid").UUID(client.post(
                    "/api/v1/sessions", json={"mode": "curiosity"}).json()["id"])
                with app.state.database.session() as db, db.begin():
                    expired_claim = claim(db, first, recovery_id, "recovery-key", payload)
                with app.state.database.session() as db, db.begin():
                    db.get(AnswerRequest, expired_claim.request_id).lease_expires_at = (
                        datetime.now(timezone.utc) - timedelta(seconds=1))
                with app.state.database.session() as db, db.begin():
                    recovered_claim = claim(db, first, recovery_id, "recovery-key", payload)
                    assert recovered_claim.token != expired_claim.token
                    with pytest.raises(HTTPException) as stale_worker:
                        finalize(db, expired_claim.request_id, expired_claim.token, "Why?",
                                 {"status": "ok", "blocks": [{"kind": "text", "text": "Stale"}]})
                    assert stale_worker.value.detail == "request_claim_lost"
                with app.state.database.session() as db, db.begin():
                    from app.modules.functional.conversations.requests import fail
                    fail(db, recovered_claim.request_id, recovered_claim.token, "provider_unavailable")
                with app.state.database.session() as db, db.begin():
                    failure_replay = claim(db, first, recovery_id, "recovery-key", payload)
                    assert failure_replay.status == "failed"
                    assert failure_replay.result["code"] == "provider_unavailable"
                    with pytest.raises(HTTPException) as changed_failure:
                        claim(db, first, recovery_id, "recovery-key", {**payload, "question": "Other"})
                    assert changed_failure.value.detail == "idempotency_key_conflict"
                assert client.get(f"/api/v1/sessions/{recovery_id}/messages").json()["items"] == []
                principal["id"] = str(second)
                assert client.get(f"/api/v1/sessions/{sid}").status_code == 404
                assert client.get(f"/api/v1/sessions/{sid}/messages").status_code == 404
                assert client.request("DELETE", f"/api/v1/sessions/{sid}", json={"confirm": True}).status_code == 404
                principal["id"] = str(first)
                assert client.request("DELETE", f"/api/v1/sessions/{sid}", json={"confirm": True}).status_code == 200
                assert client.get(f"/api/v1/sessions/{sid}").status_code == 404
                deletion_key = app.state.settings.supabase_service_role_key
                try:
                    app.state.settings.supabase_service_role_key = None
                    unavailable_delete = client.request("DELETE", "/api/v1/me", json={"confirm": True})
                    assert unavailable_delete.status_code == 503
                    assert unavailable_delete.json()["error"]["code"] == "account_deletion_unavailable"
                finally:
                    app.state.settings.supabase_service_role_key = deletion_key
                from unittest.mock import patch
                with patch("app.modules.functional.data_lifecycle.service.delete_provider_user", return_value=True) as provider_delete:
                    removed = client.request("DELETE", "/api/v1/me", json={"confirm": True})
                provider_delete.assert_called_once()
                assert removed.status_code == 200, removed.text
                with app.state.database.session() as db:
                    profile = db.get(StudentProfile, first)
                    assert profile.status == "deleted" and profile.email is None
                    assert db.get(BrowserSession, "b5-" + first.hex) is None
                assert client.get("/api/v1/sessions").json()["items"] == []
                assert client.get(f"/api/v1/admin/students/{first}").status_code == 404
                assert client.get(f"/api/v1/admin/students/{first}/activity").status_code == 404
                principal["id"] = str(second)
                with patch("app.modules.functional.data_lifecycle.service.delete_provider_user", return_value=False):
                    pending_delete = client.request("DELETE", "/api/v1/me", json={"confirm": True})
                assert pending_delete.status_code == 202, pending_delete.text
                assert pending_delete.json()["status"] == "pending_provider"
                with app.state.database.session() as db:
                    assert db.get(StudentProfile, second).status == "deleting"
                from app.modules.functional.data_lifecycle.service import complete_provider_deletion
                with patch("app.modules.functional.data_lifecycle.service.delete_provider_user", return_value=True):
                    assert complete_provider_deletion(app.state.database, app.state.settings,
                        __import__("uuid").UUID(pending_delete.json()["deletion_request_id"]))
                with app.state.database.session() as db:
                    assert db.get(StudentProfile, second).status == "deleted"
                from app.modules.functional.data_lifecycle.models import DeletionRequest
                from app.modules.functional.data_lifecycle.service import purge_completed_tombstones
                with app.state.database.session() as db, db.begin():
                    old_receipt = db.get(DeletionRequest,
                        __import__("uuid").UUID(removed.json()["deletion_request_id"]))
                    old_receipt.completed_at = datetime.now(timezone.utc) - timedelta(days=31)
                assert purge_completed_tombstones(app.state.database) == 1
                with app.state.database.session() as db:
                    assert db.get(StudentProfile, first) is None
                    assert db.get(StudentProfile, second) is not None
            finally:
                app.state.database.sessions = original
                outer.rollback()









def test_two_workers_claim_one_question():
    if os.environ.get("FLAME_RUN_DB_CONCURRENCY_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_CONCURRENCY_TESTS=1 for cleaned-up two-worker check")
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from fastapi import HTTPException
    from sqlalchemy import delete, func, select
    from app.core.database import Database
    from app.modules.functional.conversations.models import AnswerRequest, ConversationSession
    from app.modules.functional.student_activity.models import ActivityEvent

    database = Database(Settings())
    student_id, session_id = uuid4(), uuid4()
    try:
        with database.session() as db, db.begin():
            db.add(StudentProfile(id=student_id, auth_subject=str(student_id)))
            db.flush()
            db.add(ConversationSession(id=session_id, student_id=student_id, mode="curiosity"))
        barrier = Barrier(2)
        body = {"mode": "curiosity", "context": None, "question": "Why?"}
        def attempt():
            barrier.wait(timeout=5)
            try:
                with database.session() as db, db.begin():
                    return claim(db, student_id, session_id, "one-key", body).status
            except HTTPException as error:
                return error.detail
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=20) for future in
                       [pool.submit(attempt), pool.submit(attempt)]]
        assert sorted(results) == ["claimed", "request_in_progress"]
        with database.session() as db:
            count = db.scalar(select(func.count()).select_from(AnswerRequest).where(
                AnswerRequest.session_id == session_id))
            assert count == 1
    finally:
        with database.session() as db, db.begin():
            db.execute(delete(AnswerRequest).where(AnswerRequest.session_id == session_id))
            db.execute(delete(ActivityEvent).where(ActivityEvent.session_id == session_id))
            db.execute(delete(ConversationSession).where(ConversationSession.id == session_id))
            db.execute(delete(StudentProfile).where(StudentProfile.id == student_id))
        database.close()











