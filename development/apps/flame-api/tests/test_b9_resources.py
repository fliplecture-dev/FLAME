"""B9.2 media validation and rollback-only resource draft checks."""
import os
from io import BytesIO
from urllib.parse import urlsplit
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.modules.identity.dependencies import require_admin, require_member
from app.modules.identity.models import StudentProfile
from app.modules.resources.validation import MediaRejected, declared_format, validate_external_url
from app.modules.resources.storage import ResourceStorage, StorageUnavailable


def test_storage_keys_never_escape_private_root():
    with pytest.raises(StorageUnavailable):
        ResourceStorage.checked_key("../public/figure.png")


def test_b9_admin_route_requires_identity():
    app = create_app(Settings(_env_file=None, environment="test"))
    with TestClient(app) as client:
        assert client.post("/api/v1/admin/resources", json={}).status_code in (401, 403)


def test_media_declarations_and_external_hosts():
    assert declared_format("figure.PNG", "image/png")[:3] == (".png", "image/png", "image")
    for filename, mime in (("page.svg", "image/svg+xml"), ("script.html", "application/javascript"),
                           ("figure.png", "text/html"), ("movie.mp4.exe", "video/mp4")):
        with pytest.raises(MediaRejected):
            declared_format(filename, mime)
    assert validate_external_url("https://media.example.test/image.png", {"media.example.test"}) == "https://media.example.test/image.png"
    for url in ("http://media.example.test/x", "https://127.0.0.1/x",
                "https://localhost/x", "https://media.example.test.evil.test/x",
                "https://user:pass@media.example.test/x", "https://media.example.test:8443/x",
                "https://media.example.test/x#fragment", "https://media.example.test\\@evil.test/x"):
        with pytest.raises(MediaRejected):
            validate_external_url(url, {"media.example.test"})


@pytest.mark.db_integration
def test_owned_upload_and_exact_draft_association():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for rollback-only B9 database checks")
    base = Settings()
    with TemporaryDirectory() as storage_dir:
        app = create_app(Settings(_env_file=None, environment="test", database_url=base.database_url,
                                  resource_local_dir=storage_dir,
                                  resource_allowed_hosts="media.example.test",
                                  bff_shared_key="test-resource-signing-key"))
        first, second = uuid4(), uuid4()
        principal = {"id": str(first), "role": "admin"}
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
                            StudentProfile(id=first, auth_subject=str(first), display_name="First", email="first-resource@example.test"),
                            StudentProfile(id=second, auth_subject=str(second), display_name="Second", email="second-resource@example.test"),
                        ])
                    created = client.post("/api/v1/admin/curricula", json={"code": "res-" + uuid4().hex[:12], "name": "Resources"})
                    assert created.status_code == 201, created.text
                    cid = created.json()["id"]
                    def child(kind, parent_id, name):
                        response = client.post("/api/v1/admin/curriculum/" + kind, json={"parent_id": parent_id, "name": name})
                        assert response.status_code == 201, response.text
                        return response.json()["id"]
                    level = child("level", cid, "Level")
                    subject = child("subject", level, "Science")
                    domain = child("domain", subject, "Motion")
                    topic = child("topic", domain, "Gravity")
                    subtopic = child("subtopic", topic, "Falling")

                    img = Image.new("RGB", (2, 2), "red")
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    payload = buffer.getvalue()
                    bad = client.post("/api/v1/admin/resources/uploads",
                                      files={"file": ("bad.png", b"<script>bad</script>", "image/png")})
                    assert bad.status_code == 422
                    uploaded = client.post("/api/v1/admin/resources/uploads",
                                           files={"file": ("figure.png", payload, "image/png")})
                    assert uploaded.status_code == 201, uploaded.text
                    upload_id = uploaded.json()["upload_id"]
                    draft = {"type": "diagram", "title": "Gravity diagram", "upload_id": upload_id,
                             "paths": [{"topic_id": topic, "subtopic_id": subtopic}],
                             "alt_text": "Two falling objects", "rights_basis": "owned",
                             "rights_holder": "FLAME", "distribution_scope": "members"}
                    invalid = client.post("/api/v1/admin/resources", json={**draft, "paths": [{"topic_id": topic, "subtopic_id": str(uuid4())}]})
                    assert invalid.status_code == 422
                    principal["id"] = str(second)
                    assert client.post("/api/v1/admin/resources", json=draft).status_code == 404
                    principal["id"] = str(first)
                    saved = client.post("/api/v1/admin/resources", json=draft)
                    assert saved.status_code == 201, saved.text
                    assert saved.json()["published"] is False
                    assert saved.json()["paths"] == draft["paths"]
                    assert client.post("/api/v1/admin/resources", json=draft).status_code == 409
                    assert client.post("/api/v1/admin/resources", json={**draft, "upload_id": None,
                        "external_url": "https://unapproved.example.test/p.png"}).status_code == 422
                    link = client.post("/api/v1/admin/resources", json={**draft, "upload_id": None,
                        "external_url": "https://media.example.test/diagram.png"})
                    assert link.status_code == 201, link.text
                    listing = client.get("/api/v1/admin/resources", params={"type": "diagram", "published": False})
                    assert listing.status_code == 200
                    assert any(item["id"] == saved.json()["id"] for item in listing.json()["items"])
                    curriculum = client.get(f"/api/v1/admin/curricula/{cid}/tree").json()
                    published_curriculum = client.post(
                        f"/api/v1/admin/curriculum/curriculum/{cid}/publish",
                        json={"expected_version": curriculum["version"], "expected_draft_revision": curriculum["draft_revision"]})
                    assert published_curriculum.status_code == 200, published_curriculum.text
                    rid = saved.json()["id"]
                    assert client.post(f"/api/v1/admin/resources/{rid}/publish",
                        json={"expected_version": 99}).status_code == 409
                    pub = client.post(f"/api/v1/admin/resources/{rid}/publish",
                        json={"expected_version": 1})
                    assert pub.status_code == 200, pub.text
                    assert pub.json()["published"] is True
                    found = client.get("/api/v1/resources",
                                       params={"topic_id": topic, "subtopic_id": subtopic,
                                               "curriculum_revision": published_curriculum.json()["revision"]})
                    assert found.status_code == 200, found.text
                    assert found.json()["items"][0]["id"] == rid
                    assert found.json()["items"][0].get("storage_key") is None
                    stale = client.get("/api/v1/resources", params={"topic_id": topic, "curriculum_revision": 999})
                    assert stale.status_code == 409
                    delivery = client.get(f"/api/v1/resources/{rid}/delivery")
                    assert delivery.status_code == 200, delivery.text
                    signed = urlsplit(delivery.json()["url"])
                    content = client.get(signed.path + "?" + signed.query)
                    assert content.status_code == 200 and content.content == payload
                    assert content.headers["x-content-type-options"] == "nosniff"
                    expired = client.get(signed.path, params={"expires": 1, "signature": signed.query.split("signature=")[1]})
                    assert expired.status_code == 404
                    activity = {"event_type": "open", "deduplication_key": "resource-open-" + uuid4().hex}
                    first_open = client.post(f"/api/v1/resources/{rid}/activity", json=activity)
                    assert first_open.status_code == 200, first_open.text
                    again = client.post(f"/api/v1/resources/{rid}/activity", json=activity)
                    assert again.status_code == 200 and again.json()["replayed"] is True
                    withdrawn = client.post(f"/api/v1/admin/resources/{rid}/unpublish",
                                            json={"expected_version": pub.json()["version"]})
                    assert withdrawn.status_code == 200
                    assert client.get(f"/api/v1/resources/{rid}/delivery").status_code == 404
                    assert client.get(signed.path + "?" + signed.query).status_code == 404
                    assert client.get("/api/v1/resources", params={"topic_id": topic}).json()["status"] == "no_results"
                finally:
                    app.state.database.sessions = original
                    outer.rollback()
