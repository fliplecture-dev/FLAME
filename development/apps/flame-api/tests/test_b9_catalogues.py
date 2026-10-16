"""Rollback-only B9 teacher, recommendation and kit integrity checks."""
import os
from io import BytesIO
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.modules.functional.conversations.models import ConversationSession, Message
from app.modules.functional.identity.dependencies import require_admin, require_member
from app.modules.functional.identity.models import StudentProfile

pytestmark = pytest.mark.db_integration


def test_subject_recommendations_and_multi_topic_kit():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for rollback-only B9 database checks")
    base = Settings()
    with TemporaryDirectory() as storage_dir:
        app = create_app(Settings(_env_file=None, environment="test", database_url=base.database_url,
                                  resource_local_dir=storage_dir,
                                  resource_allowed_hosts="media.example.test",
                                  bff_shared_key="test-resource-signing-key"))
        member, admin = uuid4(), uuid4()
        principal = {"id": str(admin), "role": "admin"}
        app.dependency_overrides[require_admin] = lambda: principal
        app.dependency_overrides[require_member] = lambda: principal
        with TestClient(app) as client:
            with app.state.database.engine.connect() as connection:
                outer = connection.begin()
                original = app.state.database.sessions
                app.state.database.sessions = sessionmaker(
                    bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
                try:
                    with app.state.database.session() as session, session.begin():
                        session.add_all([
                            StudentProfile(id=member, auth_subject=str(member), display_name="Learner",
                                           email="learner-b9@example.test"),
                            StudentProfile(id=admin, auth_subject=str(admin), display_name="Owner",
                                           email="owner-b9@example.test"),
                        ])
                    created = client.post("/api/v1/admin/curricula", json={"code": "b9-" + uuid4().hex[:12],
                                                                            "name": "B9 sample"})
                    assert created.status_code == 201, created.text
                    cid = created.json()["id"]

                    def child(kind, parent, name):
                        response = client.post("/api/v1/admin/curriculum/" + kind,
                                               json={"parent_id": parent, "name": name})
                        assert response.status_code == 201, response.text
                        return response.json()["id"]

                    level = child("level", cid, "Level 3")
                    science = child("subject", level, "Science")
                    motion = child("domain", science, "Motion")
                    gravity = child("topic", motion, "Gravity")
                    falling = child("subtopic", gravity, "Falling objects")
                    math = child("subject", level, "Mathematics")
                    numbers = child("domain", math, "Numbers")
                    fractions = child("topic", numbers, "Fractions")
                    parts = child("subtopic", fractions, "Parts of a whole")
                    tree = client.get(f"/api/v1/admin/curricula/{cid}/tree").json()
                    pub = client.post(f"/api/v1/admin/curriculum/curriculum/{cid}/publish",
                                      json={"expected_version": tree["version"], "expected_draft_revision": tree["draft_revision"]})
                    assert pub.status_code == 200, pub.text
                    revision = pub.json()["revision"]

                    science_teacher = client.post("/api/v1/admin/teachers", json={
                        "name": "Science guide", "bio": "Explains motion",
                        "languages": ["English"], "expertise": [
                            {"subject_id": science, "claim_status": "reviewed"}]})
                    assert science_teacher.status_code == 201, science_teacher.text
                    duplicate = client.post("/api/v1/admin/teachers", json={
                        "name": "Duplicate expertise", "expertise": [
                            {"subject_id": science}, {"subject_id": science}]})
                    assert duplicate.status_code == 422
                    math_teacher = client.post("/api/v1/admin/teachers", json={
                        "name": "Math guide", "expertise": [{"subject_id": math}]})
                    assert math_teacher.status_code == 201, math_teacher.text
                    for teacher in (science_teacher, math_teacher):
                        tid = teacher.json()["id"]
                        response = client.post(f"/api/v1/admin/teachers/{tid}/publish",
                                               json={"expected_version": 1})
                        assert response.status_code == 200, response.text

                    resource = client.post("/api/v1/admin/resources", json={
                        "type": "diagram", "title": "Gravity figure",
                        "external_url": "https://media.example.test/gravity.png",
                        "paths": [{"topic_id": gravity, "subtopic_id": falling}],
                        "alt_text": "Falling ball", "rights_basis": "owned",
                        "rights_holder": "FLAME", "distribution_scope": "members"})
                    assert resource.status_code == 201, resource.text
                    rid = resource.json()["id"]
                    assert client.post(f"/api/v1/admin/resources/{rid}/publish",
                                       json={"expected_version": 1}).status_code == 200

                    image = Image.new("RGB", (2, 2), "blue")
                    data = BytesIO()
                    image.save(data, "PNG")
                    uploaded = client.post("/api/v1/admin/resources/uploads",
                                           files={"file": ("kit.png", data.getvalue(), "image/png")})
                    assert uploaded.status_code == 201, uploaded.text
                    kit_body = {"name": "Two-subject kit", "description": "A reusable activity",
                                "materials": ["Ball", "Paper"], "instructions": "Observe and compare.",
                                "supervision": "Adult supervision.", "cost": "12.50", "currency": "USD",
                                "availability": "Available", "image_upload_ids": [uploaded.json()["upload_id"]],
                                "paths": [{"topic_id": gravity}, {"topic_id": fractions}]}
                    assert client.post("/api/v1/admin/activity-kits", json={
                        **kit_body, "cost": "-1.00"}).status_code == 422
                    assert client.post("/api/v1/admin/activity-kits", json={
                        **kit_body, "currency": None}).status_code == 422
                    kit = client.post("/api/v1/admin/activity-kits", json=kit_body)
                    assert kit.status_code == 201, kit.text
                    kid = kit.json()["id"]
                    assert len(kit.json()["paths"]) == 2
                    assert client.post(f"/api/v1/admin/activity-kits/{kid}/publish",
                                       json={"expected_version": 1}).status_code == 200
                    malformed = client.post("/api/v1/admin/activity-kits", json={
                        **kit_body, "supplier_url": "https://[broken"})
                    assert malformed.status_code == 422
                    for topic_id in (gravity, fractions):
                        listing = client.get("/api/v1/admin/activity-kits", params={"topic_id": topic_id})
                        assert sum(item["id"] == kid for item in listing.json()["items"]) == 1

                    with app.state.database.session() as session, session.begin():
                        study = ConversationSession(student_id=member, mode="study", curriculum_id=cid,
                            revision=revision, context_snapshot={
                                "curriculum_id": cid, "level_id": level, "subject_id": science,
                                "domain_id": motion, "category_id": None,
                                "topic_id": gravity, "subtopic_id": falling})
                        session.add(study)
                        session.flush()
                        session.add(Message(session_id=study.id, turn_number=1, role="user",
                                            blocks=[{"kind": "text", "text": "explain gravity"}]))
                        answer = Message(session_id=study.id, turn_number=1, role="assistant",
                                         blocks=[{"kind": "text", "text": "Gravity pulls objects."}],
                                         resolved_curriculum_id=cid, resolved_subject_id=science,
                                         resolved_topic_id=gravity, resolved_revision=revision)
                        session.add(answer)
                        curiosity = ConversationSession(student_id=member, mode="curiosity")
                        session.add(curiosity)
                        session.flush()
                        open_answer = Message(session_id=curiosity.id, turn_number=1, role="assistant",
                                              blocks=[{"kind": "text", "text": "Hello."}])
                        session.add(open_answer)
                        session.flush()
                        math_study = ConversationSession(student_id=member, mode="study", curriculum_id=cid,
                            revision=revision, context_snapshot={
                                "curriculum_id": cid, "level_id": level, "subject_id": math,
                                "domain_id": numbers, "category_id": None,
                                "topic_id": fractions, "subtopic_id": parts})
                        session.add(math_study)
                        session.flush()
                        math_answer = Message(session_id=math_study.id, turn_number=1, role="assistant",
                            blocks=[{"kind": "text", "text": "Fractions are parts."}],
                            resolved_curriculum_id=cid, resolved_subject_id=math,
                            resolved_topic_id=fractions, resolved_revision=revision)
                        session.add(math_answer)
                        session.flush()
                        math_sid, math_mid = str(math_study.id), str(math_answer.id)
                        sid, mid = str(study.id), str(answer.id)
                        curiosity_id, open_id = str(curiosity.id), str(open_answer.id)
                    principal["id"], principal["role"] = str(member), "member"
                    result = client.get(f"/api/v1/sessions/{sid}/recommendations",
                                        params={"message_id": mid})
                    assert result.status_code == 200, result.text
                    assert result.json()["teachers"] == []  # Human help must be explicitly requested.
                    assert [item["id"] for item in result.json()["resources"]] == [rid]
                    replay = client.get(f"/api/v1/sessions/{sid}/recommendations",
                                        params={"message_id": mid})
                    assert replay.json() == result.json()
                    math_result = client.get(f"/api/v1/sessions/{math_sid}/recommendations",
                        params={"message_id": math_mid})
                    assert math_result.status_code == 200, math_result.text
                    assert math_result.json()["teachers"] == []
                    assert math_result.json()["resources"] == []
                    open_result = client.get(f"/api/v1/sessions/{curiosity_id}/recommendations",
                                             params={"message_id": open_id})
                    assert open_result.json()["teachers"] == []
                    assert client.get(f"/api/v1/sessions/{sid}/recommendations",
                                      params={"message_id": open_id}).status_code == 404
                    principal["id"], principal["role"] = str(admin), "admin"
                    assert client.post(f"/api/v1/admin/teachers/{science_teacher.json()['id']}/unpublish",
                                       json={"expected_version": 2}).status_code == 200
                    principal["id"], principal["role"] = str(member), "member"
                    withdrawn = client.get(f"/api/v1/sessions/{sid}/recommendations",
                                           params={"message_id": mid})
                    assert withdrawn.json()["teachers"] == []
                    assert [item["id"] for item in withdrawn.json()["resources"]] == [rid]
                finally:
                    app.state.database.sessions = original
                    outer.rollback()
