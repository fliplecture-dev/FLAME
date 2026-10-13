from unittest.mock import Mock
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from app.core.config import Settings
from app.core.database import Database
from app.main import create_app
from app.modules.teaching.schemas import AnswerRequest, DirectAnswer, TableBlock


def app_for_test():
    return create_app(Settings(_env_file=None, environment="test", database_url=None))


def test_liveness_and_unconfigured_readiness():
    with TestClient(app_for_test()) as client:
        live = client.get("/health/live")
        assert live.status_code == 200
        assert live.headers["x-request-id"]
        ready = client.get("/health/ready")
        assert ready.status_code == 503
        assert ready.json()["error"]["code"] == "dependency_unavailable"
        assert ready.json()["request_id"] == ready.headers["x-request-id"]


def test_readiness_success_and_failure():
    application = app_for_test()
    with TestClient(application) as client:
        application.state.database.ready = Mock(return_value=True)
        assert client.get("/health/ready").status_code == 200
        application.state.database.ready = Mock(return_value=False)
        assert client.get("/health/ready").status_code == 503


def test_database_failure_is_sanitized():
    database = Database(Settings(_env_file=None, database_url=None))
    database.engine = Mock()
    database.engine.connect.side_effect = RuntimeError("secret password")
    assert database.ready() is False
    database.close()
    database.engine.dispose.assert_called_once()


def test_errors_and_request_ids():
    application = app_for_test()

    @application.get("/test/fail")
    def fail():
        raise RuntimeError("secret-provider-key")

    @application.get("/test/value")
    def value(number: int):
        return number

    with TestClient(application) as client:
        for path, status, code in [
            ("/missing", 404, "not_found"),
            ("/test/fail", 500, "internal_error"),
            ("/test/value?number=secret-provider-key", 422, "validation_error"),
        ]:
            result = client.get(path)
            assert result.status_code == status
            assert result.json()["error"]["code"] == code
            assert "secret-provider-key" not in result.text
            assert result.json()["request_id"] == result.headers["x-request-id"]
        assert client.post("/health/live").status_code == 405


def test_settings_fail_fast_and_mask_secrets():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", database_url=None)
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="sqlite:///local.db")
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_connect_timeout=0)
    settings = Settings(_env_file=None, database_url="postgresql+psycopg://u:password@localhost/flame")
    assert "password" not in repr(settings)


def test_production_docs_disabled():
    application = create_app(Settings(
        _env_file=None, environment="production",
        database_url="postgresql+psycopg://u:p@localhost/flame",
        supabase_url="https://sample.supabase.co",
        supabase_anon_key="test-key",
        supabase_service_role_key="test-service-role-key",
        session_encryption_key="test-key",
        web_origin="https://flame.example",
        bff_shared_key="test-secret",
        resource_storage_backend="supabase",
        resource_storage_bucket="private-test-resources",
    ))
    with TestClient(application) as client:
        assert client.get("/docs").status_code == 404
        assert client.get("/openapi.json").status_code == 404


def test_request_contract_rejects_client_authority():
    assert AnswerRequest(question=" Why? ", mode="curiosity").question == "Why?"
    for values in [
        {"question": " ", "mode": "curiosity"},
        {"question": "Why?", "mode": "study"},
        {"question": "Why?", "mode": "curiosity", "student_id": "another"},
        {"question": "Why?", "mode": "curiosity", "history": []},
        {"question": "Why?", "mode": "curiosity", "attachments": []},
    ]:
        with pytest.raises(ValidationError):
            AnswerRequest(**values)


@pytest.mark.parametrize("with_category", [False, True])
def test_study_context_hierarchy(with_category):
    from uuid import uuid4
    context = {key: uuid4() for key in ("curriculum_id", "level_id", "subject_id", "domain_id", "topic_id", "subtopic_id")}
    if with_category:
        context["category_id"] = uuid4()
    request = AnswerRequest(question="Explain this topic", mode="study", context=context)
    assert request.context.curriculum_id == context["curriculum_id"]
    assert request.context.domain_id == context["domain_id"]
    assert request.context.category_id == context.get("category_id")
    assert request.context.subtopic_id == context["subtopic_id"]
    topic_request = AnswerRequest(question="Explain", mode="study",
                                  context={key: value for key, value in context.items() if key != "subtopic_id"})
    assert topic_request.context.subtopic_id is None
    with pytest.raises(ValidationError):
        AnswerRequest(question="Explain", mode="study",
                      context={key: value for key, value in context.items() if key != "domain_id"})
    with pytest.raises(ValidationError):
        AnswerRequest(question="Explain", mode="study", context={**context, "category_id": "invalid"})


def test_output_contract_rejects_false_provenance():
    from uuid import uuid4
    values = dict(response_id=uuid4(), request_id=uuid4(), curriculum_version="v1",
                  blocks=[{"id": "b1", "kind": "text", "text": "Example"}])
    assert DirectAnswer(**values).grounded is False
    with pytest.raises(ValidationError):
        DirectAnswer(**values, grounded=True)
    with pytest.raises(ValidationError):
        DirectAnswer(**values, citations=["invented"])
    with pytest.raises(ValidationError):
        TableBlock(id="b", kind="table", caption="Example", columns=["A"], rows=[["a", "b"]])


def test_openapi_only_exposes_implemented_routes():
    with TestClient(app_for_test()) as client:
        paths = client.get("/openapi.json").json()["paths"]
        assert {"/health/live", "/health/ready", "/api/v1/me", "/api/v1/auth/login", "/api/v1/auth/register"} <= set(paths)
        assert "/api/v1/curricula" in paths
        assert "/api/v1/me/learning" in paths
        assert "/api/v1/sessions" in paths


@pytest.mark.parametrize("curriculum_id", [None, "not-a-uuid"])
def test_study_rejects_invalid_curriculum(curriculum_id):
    from uuid import uuid4
    context = {key: uuid4() for key in ("level_id", "subject_id", "domain_id", "topic_id", "subtopic_id")}
    context["curriculum_id"] = curriculum_id
    with pytest.raises(ValidationError):
        AnswerRequest(question="Explain", mode="study", context=context)


def test_study_requires_curriculum_and_preserves_distinct_roots():
    from uuid import uuid4
    context = {key: uuid4() for key in ("level_id", "subject_id", "domain_id", "topic_id", "subtopic_id")}
    with pytest.raises(ValidationError) as error:
        AnswerRequest(question="Explain", mode="study", context=context)
    assert any(e["loc"] == ("context", "curriculum_id") and e["type"] == "missing"
               for e in error.value.errors())
    roots = [uuid4(), uuid4()]
    requests = [AnswerRequest(question="Explain", mode="study",
                             context={**context, "curriculum_id":root}) for root in roots]
    assert [r.context.curriculum_id for r in requests] == roots
    # Shape validation preserves IDs; B2/B4 must reject cross-curriculum ancestry in DB.


