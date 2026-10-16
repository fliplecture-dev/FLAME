"""Rollback-only B4 catalogue and membership integration checks."""
import os
from io import BytesIO
from openpyxl import Workbook
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.modules.functional.identity.dependencies import require_admin, require_member
from app.modules.functional.identity.models import AdminRole, StudentProfile

pytestmark = pytest.mark.db_integration


def test_catalogue_publication_membership_and_isolation():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for rollback-only B4 database tests")
    settings = Settings()
    app = create_app(Settings(_env_file=None, environment="test", database_url=settings.database_url))
    first, second, admin = uuid4(), uuid4(), uuid4()
    principal = {"id": str(first), "role": "member"}
    app.dependency_overrides[require_member] = lambda: principal
    app.dependency_overrides[require_admin] = lambda: {"id": str(admin), "role": "admin"}

    with TestClient(app) as client:
        with app.state.database.engine.connect() as connection:
            outer = connection.begin()
            original = app.state.database.sessions
            app.state.database.sessions = sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
            try:
                with app.state.database.session() as session, session.begin():
                    session.add_all([
                        StudentProfile(id=first, auth_subject=str(first), display_name="First", email="first@example.test"),
                        StudentProfile(id=second, auth_subject=str(second), display_name="Second", email="second@example.test"),
                        StudentProfile(id=admin, auth_subject=str(admin), display_name="Admin", email="admin@example.test"),
                        AdminRole(auth_subject=str(admin)),
                    ])
                code = "b4-" + uuid4().hex[:12]
                created = client.post("/api/v1/admin/curricula", json={"code": code, "name": "Test curriculum"})
                assert created.status_code == 201, created.text
                curriculum = created.json()
                cid = curriculum["id"]
                empty = client.post("/api/v1/admin/curricula",
                    json={"code": "empty-" + uuid4().hex[:12], "name": "Unused draft"}).json()
                listed = client.get("/api/v1/admin/curricula", params={"q": empty["code"]}).json()["items"][0]
                assert listed["updated_at"]
                assert client.request("DELETE", "/api/v1/admin/curricula/" + empty["id"],
                    json={"expected_version": empty["version"] + 1}).status_code == 409
                assert client.request("DELETE", "/api/v1/admin/curricula/" + empty["id"],
                    json={"expected_version": empty["version"]}).status_code == 200

                def child(kind, parent_id, name, **extra):
                    response = client.post("/api/v1/admin/curriculum/" + kind,
                                           json={"parent_id": parent_id, "name": name, **extra})
                    assert response.status_code == 201, response.text
                    return response.json()["id"]

                removable = client.post("/api/v1/admin/curricula", json={
                    "code": "remove-" + uuid4().hex[:12], "name": "Removable curriculum"}).json()
                removable_id = removable["id"]
                removed_level = child("level", removable_id, "Grade 1")
                removed_subject = child("subject", removed_level, "Science")
                removed_domain = child("domain", removed_subject, "Motion")
                removed_topic = child("topic", removed_domain, "Gravity")
                child("subtopic", removed_topic, "Falling")
                removable_revision = client.get(f"/api/v1/admin/curricula/{removable_id}/tree").json()["draft_revision"]
                orbit = client.post(f"/api/v1/admin/curricula/{removable_id}/paths/batch", json={
                    "expected_revision": removable_revision, "changes": [{
                        "key": "orbit", "action": "upsert", "values": {
                            "level": "Grade 1", "subject": "Science", "domain": "Motion",
                            "category": None, "topic": "Gravity", "subtopic": "Orbit"}}]})
                assert orbit.status_code == 200, orbit.text
                orbit_id = orbit.json()["rows"][0]["subtopic_id"]
                moved = client.post(f"/api/v1/admin/curricula/{removable_id}/paths/batch", json={
                    "expected_revision": orbit.json()["draft_revision"], "changes": [{
                        "key": "physics", "action": "upsert", "source_subtopic_id": orbit_id,
                        "values": {"level": "Grade 1", "subject": "Physics",
                                   "domain": "Motion", "category": None,
                                   "topic": "Gravity", "subtopic": "Orbit"}}]})
                assert moved.status_code == 200, moved.text
                assert client.post(f"/api/v1/admin/curricula/{removable_id}/paths/batch", json={
                    "expected_revision": orbit.json()["draft_revision"], "changes": [{
                        "key": "stale", "action": "delete",
                        "source_subtopic_id": moved.json()["rows"][0]["subtopic_id"]}]}).status_code == 409
                removable_tree = client.get(f"/api/v1/admin/curricula/{removable_id}/tree").json()
                assert client.post(f"/api/v1/admin/curriculum/curriculum/{removable_id}/publish",
                    json={"expected_version": removable_tree["version"],
                          "expected_draft_revision": removable_tree["draft_revision"]}).status_code == 200
                review = client.get(f"/api/v1/admin/curricula/{removable_id}/deletion-review")
                assert review.status_code == 200, review.text
                assert review.json()["counts"]["hierarchy_nodes"] >= 5
                assert review.json()["counts"]["published_revisions"] == 1
                assert review.json()["can_delete"] is True
                assert client.post(f"/api/v1/admin/curricula/{removable_id}/permanent", json={
                    "expected_version": review.json()["version"],
                    "expected_revision": review.json()["revision"],
                    "confirm": "wrong"}).status_code == 422
                assert client.post(f"/api/v1/admin/curricula/{removable_id}/permanent", json={
                    "expected_version": review.json()["version"],
                    "expected_revision": review.json()["revision"] + 1,
                    "confirm": removable["code"]}).status_code == 409
                draft_before_archive = client.get(f"/api/v1/admin/curricula/{removable_id}/tree").json()
                archived_curriculum = client.post(
                    f"/api/v1/admin/curriculum/curriculum/{removable_id}/archive",
                    json={"expected_version": review.json()["version"]})
                assert archived_curriculum.status_code == 200
                restored = client.post(f"/api/v1/admin/curricula/{removable_id}/restore",
                    json={"expected_version": archived_curriculum.json()["version"]})
                assert restored.status_code == 200 and restored.json()["state"] == "draft"
                restored_tree = client.get(f"/api/v1/admin/curricula/{removable_id}/tree").json()
                assert restored_tree["draft_revision"] == draft_before_archive["draft_revision"]
                republished = client.post(f"/api/v1/admin/curriculum/curriculum/{removable_id}/publish",
                    json={"expected_version": restored_tree["version"],
                          "expected_draft_revision": restored_tree["draft_revision"]})
                assert republished.status_code == 200, republished.text
                archived_again = client.post(
                    f"/api/v1/admin/curriculum/curriculum/{removable_id}/archive",
                    json={"expected_version": republished.json()["version"]})
                assert archived_again.status_code == 200, archived_again.text
                restored_again = client.post(f"/api/v1/admin/curricula/{removable_id}/restore",
                    json={"expected_version": archived_again.json()["version"]})
                assert restored_again.status_code == 200, restored_again.text
                review = client.get(f"/api/v1/admin/curricula/{removable_id}/deletion-review").json()
                deleted = client.post(f"/api/v1/admin/curricula/{removable_id}/permanent", json={
                    "expected_version": review["version"], "expected_revision": review["revision"],
                    "confirm": removable["code"]})
                assert deleted.status_code == 200, deleted.text
                assert client.get(f"/api/v1/admin/curricula/{removable_id}/deletion-review").status_code == 404

                temporary = child("level", cid, "Temporary")
                assert client.request("DELETE", f"/api/v1/admin/curriculum/level/{temporary}",
                    json={"expected_version": 1}).status_code == 200
                level = child("level", cid, "Level 1")
                subject = child("subject", level, "Science")
                assert client.request("DELETE", f"/api/v1/admin/curriculum/level/{level}",
                    json={"expected_version": 1}).status_code == 409
                assert client.request("DELETE", "/api/v1/admin/curricula/" + cid,
                    json={"expected_version": curriculum["version"]}).status_code == 409
                domain = child("domain", subject, "Motion")
                category = child("category", domain, "Forces")
                topic = child("topic", domain, "Gravity", category_id=category)
                subtopic = child("subtopic", topic, "Falling objects")
                tree = client.get(f"/api/v1/curricula/{cid}/levels/{level}/tree")
                assert tree.status_code == 404
                admin_tree = client.get(f"/api/v1/admin/curricula/{cid}/tree").json()
                stale_publish = client.post(f"/api/v1/admin/curriculum/curriculum/{cid}/publish",
                    json={"expected_version": admin_tree["version"],
                          "expected_draft_revision": admin_tree["draft_revision"] + 1})
                assert stale_publish.status_code == 409, stale_publish.text
                assert stale_publish.json()["error"]["code"] == "updated_elsewhere"
                published = client.post(f"/api/v1/admin/curriculum/curriculum/{cid}/publish",
                                        json={"expected_version": admin_tree["version"],
                                              "expected_draft_revision": admin_tree["draft_revision"]})
                assert published.status_code == 200, published.text
                whole_tree = client.get(f"/api/v1/curricula/{cid}/tree")
                assert whole_tree.status_code == 200, whole_tree.text
                assert whole_tree.json()["levels"][0]["id"] == level
                data = client.get(f"/api/v1/curricula/{cid}/levels/{level}/tree").json()
                assert data["levels"][0]["subjects"][0]["domains"][0]["categories"][0]["topics"][0]["subtopics"][0]["name"] == "Falling objects"

                invalid = client.post("/api/v1/me/learning", json={"curriculum_id": cid, "level_id": str(uuid4()), "subject_id": subject})
                assert invalid.status_code == 422
                added = client.post("/api/v1/me/learning", json={"curriculum_id": cid, "level_id": level, "subject_id": subject})
                assert added.status_code == 200, added.text
                member = added.json()
                duplicate = client.post("/api/v1/me/learning", json={"curriculum_id": cid, "level_id": level, "subject_id": subject})
                assert duplicate.json()["id"] == member["id"]
                full_path = {"curriculum_id": cid, "level_id": level, "subject_id": subject,
                             "domain_id": domain, "category_id": category, "topic_id": topic,
                             "subtopic_id": subtopic}
                exact = client.post("/api/v1/me/learning", json=full_path)
                assert exact.status_code == 200, exact.text
                assert exact.json()["subtopic_id"] == subtopic
                assert client.post("/api/v1/me/learning", json=full_path).json()["id"] == exact.json()["id"]
                bad_path = {**full_path, "category_id": str(uuid4())}
                assert client.post("/api/v1/me/learning", json=bad_path).status_code == 422
                principal["id"] = str(second)
                assert client.get("/api/v1/me/learning").json()["items"] == []
                assert client.patch("/api/v1/me/learning/" + member["id"], json={"visible": False, "expected_version": member["version"]}).status_code == 404
                principal["id"] = str(first)
                hidden = client.patch("/api/v1/me/learning/" + member["id"], json={"visible": False, "expected_version": member["version"]})
                assert hidden.status_code == 200, hidden.text
                restored = client.post("/api/v1/me/learning", json={"curriculum_id": cid, "level_id": level, "subject_id": subject})
                assert restored.json()["id"] == member["id"]
                assert restored.json()["visible"] is True
                assert client.get("/api/v1/admin/students", params={"q": "first@example.test"}).json()["total"] >= 1
                assert client.get("/api/v1/admin/students", params={"q": "admin@example.test"}).json()["items"] == []
                student_detail = client.get("/api/v1/admin/students/" + str(first)).json()
                assert any(item["id"] == member["id"] for item in student_detail["learning"])
                found = client.get("/api/v1/curricula/search", params={"q": "Falling"}).json()["items"]
                assert any(item["subtopic_id"] == subtopic and item["category_id"] == category for item in found)
                subtopic_version = next(item["version"] for item in client.get(
                    f"/api/v1/admin/curricula/{cid}/tree").json()["levels"][0]["subjects"][0]["domains"][0]["categories"][0]["topics"][0]["subtopics"]
                    if item["id"] == subtopic)
                blocked = client.post(f"/api/v1/admin/curriculum/subtopic/{subtopic}/archive",
                                      json={"expected_version": subtopic_version})
                assert blocked.status_code == 422
                book = Workbook()
                sheet = book.active
                sheet.title = "Level 1"
                sheet.append(["Curriculum Code", "Level", "Subject", "Domain", "Category",
                              "Topic", "Subtopic", "Learning Outcome", "Source URL"])
                sheet.append([code, "Level 1", "Science", "Motion", None,
                              "Inertia", None, None, None])
                stream = BytesIO()
                book.save(stream)
                uploaded = client.post("/api/v1/admin/curriculum/imports",
                    params={"curriculum_id": cid},
                    files={"file": ("b4.xlsx", stream.getvalue(),
                                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")})
                assert uploaded.status_code == 201, uploaded.text
                batch_id = uploaded.json()["import_id"]
                assert uploaded.json()["sheets"] == ["Level 1"]
                source_rows = client.get(f"/api/v1/admin/curriculum/imports/{batch_id}/source-rows")
                assert source_rows.status_code == 200, source_rows.text
                assert source_rows.json()["items"][0]["values"][:2] == [code, "Level 1"]
                assert source_rows.json()["total"] == 1
                preview = client.post(f"/api/v1/admin/curriculum/imports/{batch_id}/preview",
                                      json={"sheet_levels": {"Level 1": "Level 1"}})
                assert preview.status_code == 200, preview.text
                assert preview.json()["issue_count"] > 0
                review_rows = client.get(
                    f"/api/v1/admin/curriculum/imports/{batch_id}/review-rows").json()
                assert review_rows["total"] == 1
                assert review_rows["items"][0]["values"][4] == "Inertia"
                corrected = client.post(
                    f"/api/v1/admin/curriculum/imports/{batch_id}/review",
                    json={"preview_revision": preview.json()["preview_revision"],
                          "changes": [{"sheet": "Level 1", "row_number": 2,
                                       "action": "upsert",
                                       "values": ["Level 1", "Science", "Motion", "",
                                                  "Inertia", "Objects keep moving"]}]})
                assert corrected.status_code == 200, corrected.text
                assert corrected.json()["issue_count"] == 0
                assert client.get(
                    f"/api/v1/admin/curriculum/imports/{batch_id}/review-rows"
                ).json()["items"][0]["values"][5] == "Objects keep moving"
                preview = corrected
                child("subtopic", topic, "Changing catalogue revision")
                stale = client.post(f"/api/v1/admin/curriculum/imports/{batch_id}/commit",
                    headers={"idempotency-key": "b4-stale-import"},
                    json={"preview_revision": preview.json()["preview_revision"],
                          "confirm": "REPLACE " + code})
                assert stale.status_code == 409 and stale.json()["error"]["code"] == "stale_preview"
                preview = client.post(f"/api/v1/admin/curriculum/imports/{batch_id}/preview",
                                      json={"sheet_levels": {"Level 1": "Level 1"}})
                assert preview.status_code == 200, preview.text
                committed = client.post(f"/api/v1/admin/curriculum/imports/{batch_id}/commit",
                    headers={"idempotency-key": "b4-test-import"},
                    json={"preview_revision": preview.json()["preview_revision"],
                          "confirm": "REPLACE " + code})
                assert committed.status_code == 200, committed.text
                replay = client.post(f"/api/v1/admin/curriculum/imports/{batch_id}/commit",
                    headers={"idempotency-key": "b4-test-import"},
                    json={"preview_revision": preview.json()["preview_revision"],
                          "confirm": "REPLACE " + code})
                assert replay.json() == committed.json()
                history = client.get("/api/v1/admin/curriculum/imports",
                                     params={"curriculum_id": cid}).json()["items"]
                assert any(item["import_id"] == batch_id for item in history)
                # A replacement commit stays private until an explicit publication.
                assert any(item["subtopic_id"] == subtopic for item in client.get(
                    "/api/v1/curricula/search", params={"q": "Falling"}).json()["items"])
                replacement_tree = client.get(
                    f"/api/v1/admin/curricula/{cid}/tree").json()
                assert replacement_tree["levels"][0]["subjects"][0]["domains"][0][
                    "topics"][0]["subtopics"][0]["name"] == "Objects keep moving"
                exported = client.get(
                    f"/api/v1/admin/curricula/{cid}/export", params={"source": "draft"})
                assert exported.status_code == 200
                assert exported.headers["content-type"].startswith(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                published_replacement = client.post(
                    f"/api/v1/admin/curriculum/curriculum/{cid}/publish",
                    json={"expected_version": replacement_tree["version"],
                          "expected_draft_revision": replacement_tree["draft_revision"]})
                assert published_replacement.status_code == 200, published_replacement.text
                remaining = client.get(
                    "/api/v1/curricula/search", params={"q": "Falling"}).json()["items"]
                assert all(item["subtopic_id"] != subtopic for item in remaining)
                assert client.get(
                    "/api/v1/curricula/search",
                    params={"q": "Objects keep moving"}).json()["items"]
                assert client.post("/api/v1/me/learning", json=full_path).status_code == 422
                assert any(item["id"] == exact.json()["id"] for item in client.get("/api/v1/me/learning").json()["items"])
                blocked_review = client.get(f"/api/v1/admin/curricula/{cid}/deletion-review").json()
                assert blocked_review["can_delete"] is False
                assert blocked_review["counts"]["student_associations"] >= 1
                blocked_delete = client.post(f"/api/v1/admin/curricula/{cid}/permanent", json={
                    "expected_version": blocked_review["version"],
                    "expected_revision": blocked_review["revision"], "confirm": code})
                assert blocked_delete.status_code == 409
                changes = client.get(f"/api/v1/admin/curricula/{cid}/revisions").json()["items"]
                assert any(item["change_kind"] == "publish" for item in changes)
            finally:
                app.state.database.sessions = original
                outer.rollback()


def test_signed_in_member_learning_survives_new_requests_and_is_isolated():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for rollback-only B4 database tests")
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch
    import jwt
    from app.modules.functional.curriculum.models import Curriculum, Level, Subject

    current = Settings()
    secret = "b4-session-test-key"
    issuer = "https://b4-test.supabase.co/auth/v1"
    app = create_app(Settings(
        _env_file=None, environment="test", database_url=current.database_url,
        session_encryption_key=current.session_encryption_key,
        supabase_url="https://b4-test.supabase.co", supabase_anon_key="test-key",
        supabase_jwt_secret=secret, bff_shared_key="b4-test-bff"))
    def signed(subject):
        now = datetime.now(timezone.utc)
        return jwt.encode({
            "iss": issuer, "aud": "authenticated", "sub": str(subject),
            "role": "authenticated", "email": str(subject) + "@example.test",
            "iat": int(now.timestamp()), "exp": int((now + timedelta(minutes=10)).timestamp()),
        }, secret, algorithm="HS256")

    with TestClient(app) as client:
        with app.state.database.engine.connect() as connection:
            outer = connection.begin()
            original = app.state.database.sessions
            app.state.database.sessions = sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
            try:
                cid, lid, sid = uuid4(), uuid4(), uuid4()
                with app.state.database.session() as session, session.begin():
                    session.add(Curriculum(id=cid, code="b4-session-" + cid.hex[:8],
                        normalized_code="b4-session-" + cid.hex[:8], name="Session test", state="published"))
                    session.add(Level(id=lid, curriculum_id=cid, code="L1", normalized_code="l1",
                        name="L1", normalized_name="l1"))
                    session.add(Subject(id=sid, level_id=lid, name="Science", normalized_name="science"))
                first, second = uuid4(), uuid4()
                def login(subject):
                    with patch("app.modules.functional.identity.router._provider", side_effect=[
                        {"access_token": signed(subject), "refresh_token": "refresh"},
                        {"email_confirmed_at": "2026-09-26T00:00:00Z"},
                    ]):
                        response = client.post("/api/v1/auth/login",
                            headers={"x-bff-key": "b4-test-bff"},
                            json={"email": str(subject) + "@example.test", "password": "test-password"})
                    assert response.status_code == 200, response.text
                    return {"x-bff-key": "b4-test-bff", "x-flame-session": response.json()["session"]}
                own = login(first)
                saved = client.post("/api/v1/me/learning", headers=own,
                    json={"curriculum_id": str(cid), "level_id": str(lid), "subject_id": str(sid)})
                assert saved.status_code == 200, saved.text
                assert client.post("/api/v1/auth/refresh", headers=own).status_code == 200
                assert client.get("/api/v1/me/learning", headers=own).json()["items"][0]["id"] == saved.json()["id"]
                other = login(second)
                assert client.get("/api/v1/me/learning", headers=other).json()["items"] == []
                assert client.post("/api/v1/auth/logout", headers=own).status_code == 200
                assert client.get("/api/v1/me/learning", headers=own).status_code == 401
            finally:
                app.state.database.sessions = original
                outer.rollback()


def test_concurrent_same_path_additions_are_serialized_and_deduplicated():
    if os.environ.get("FLAME_RUN_DB_CONCURRENCY_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_CONCURRENCY_TESTS=1 for the cleaned-up concurrency check")
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    from types import SimpleNamespace
    from sqlalchemy import delete, select
    from app.core.database import Database
    from app.modules.functional.curriculum.models import Curriculum
    from app.modules.functional.curriculum.router import LearningAdd, add_learning
    from app.modules.functional.learning.models import LearningMembership

    database = Database(Settings())
    cid, student_id = uuid4(), uuid4()
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database=database)))
    try:
        with database.session() as session, session.begin():
            session.add(Curriculum(id=cid, code="b4-race-" + cid.hex[:8],
                                   normalized_code="b4-race-" + cid.hex[:8],
                                   name="Concurrency fixture", state="published"))
            session.add(StudentProfile(id=student_id, auth_subject=str(student_id),
                                       display_name="Concurrency fixture"))
        barrier = Barrier(2)
        def add_once():
            barrier.wait(timeout=5)
            return add_learning(request, LearningAdd(curriculum_id=cid),
                                {"id": str(student_id), "role": "member"})
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(add_once) for _ in range(2)]
            results = [future.result(timeout=15) for future in futures]
        assert results[0]["id"] == results[1]["id"]
        with database.session() as session:
            rows = session.scalars(select(LearningMembership).where(
                LearningMembership.student_id == student_id,
                LearningMembership.curriculum_id == cid)).all()
            assert len(rows) == 1
    finally:
        with database.session() as session, session.begin():
            session.execute(delete(LearningMembership).where(
                LearningMembership.student_id == student_id,
                LearningMembership.curriculum_id == cid))
            session.execute(delete(Curriculum).where(Curriculum.id == cid))
            session.execute(delete(StudentProfile).where(StudentProfile.id == student_id))
        database.close()


