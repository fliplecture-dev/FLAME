from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.core.config import Settings
from app.main import create_app
from app.modules.identity.dependencies import require_admin, require_owner
from app.modules.identity.router import RegisterBody, verify_access_token


def settings():
    return Settings(_env_file=None, environment="test",
                    supabase_url="https://sample.supabase.co",
                    supabase_jwt_secret="test-signing-secret",
                    bff_shared_key="test-bff-secret")


def token(*, sub="00000000-0000-4000-8000-000000000001", exp=None, audience="authenticated", issuer=None, role="authenticated"):
    now = datetime.now(timezone.utc)
    return jwt.encode({"iss": issuer or "https://sample.supabase.co/auth/v1",
                       "aud": audience, "sub": sub, "iat": int(now.timestamp()),
                       "exp": int((exp or (now + timedelta(minutes=5))).timestamp()),
                       "role": role}, "test-signing-secret", algorithm="HS256")


def test_jwt_checks_signature_issuer_audience_expiry_subject_and_role():
    assert verify_access_token(settings(), token())["sub"] == "00000000-0000-4000-8000-000000000001"
    invalid = [
        token(sub=""), token(audience="elsewhere"),
        token(issuer="https://other.example/auth/v1"),
        token(exp=datetime.now(timezone.utc) - timedelta(minutes=2)),
        token(role="service_role"),
        jwt.encode(jwt.decode(token(), options={"verify_signature": False}), "wrong-secret", algorithm="HS256"),
    ]
    for value in invalid:
        try:
            verify_access_token(settings(), value)
            assert False, "invalid JWT accepted"
        except Exception as exc:
            assert getattr(exc, "status_code", None) == 401


def test_identity_routes_require_bff_secret():
    with TestClient(create_app(settings())) as client:
        for method, path in [("get", "/api/v1/me"), ("post", "/api/v1/auth/login"),
                             ("post", "/api/v1/auth/register")]:
            response = getattr(client, method)(path)
            assert response.status_code == 403


def test_registration_is_generic_for_duplicate_provider_error():
    with TestClient(create_app(settings())) as client:
        from fastapi import HTTPException
        with patch("app.modules.identity.router._provider", side_effect=HTTPException(401)):
            response = client.post("/api/v1/auth/register", headers={"x-bff-key": "test-bff-secret"},
                                   json={"email": "member@example.com", "password": "long-test-password", "display_name": "Member"})
            assert response.status_code == 200
            assert response.json() == {"status": "verification_pending"}


def test_no_admin_self_selection_and_owner_denial():
    try:
        RegisterBody(email="member@example.com", password="long-test-password", display_name="Member", role="admin")
        assert False
    except ValidationError:
        pass
    from fastapi import HTTPException
    try:
        require_admin({"id": "member-1", "role": "member"})
        assert False
    except HTTPException as exc:
        assert exc.status_code == 403
    from uuid import uuid4
    try:
        require_owner({"id": str(uuid4()), "role": "member"}, uuid4())
        assert False
    except HTTPException as exc:
        assert exc.status_code == 404

def test_unverified_login_and_invalid_callback_are_denied():
    payload = {"access_token": "private-access", "refresh_token": "private-refresh"}
    with TestClient(create_app(settings())) as client:
        with patch("app.modules.identity.router._provider", side_effect=[payload, {"email_confirmed_at": None}]):
            response = client.post("/api/v1/auth/login", headers={"x-bff-key": "test-bff-secret"},
                                   json={"email": "member@example.com", "password": "secret"})
            assert response.status_code == 401
            assert "private-" not in response.text
        response = client.post("/api/v1/auth/verify", headers={"x-bff-key": "test-bff-secret"},
                               json={"token_hash": "hash", "type": "admin"})
        assert response.status_code == 422


def test_recovery_does_not_enumerate_unknown_email():
    from fastapi import HTTPException
    with TestClient(create_app(settings())) as client:
        with patch("app.modules.identity.router._provider", side_effect=HTTPException(401)):
            response = client.post("/api/v1/auth/recover", headers={"x-bff-key": "test-bff-secret"},
                                   json={"email": "unknown@example.com"})
            assert response.status_code == 200
            assert response.json() == {"status": "recovery_sent"}


def test_revoked_browser_session_is_denied_before_token_decryption():
    from types import SimpleNamespace
    from unittest.mock import MagicMock
    from app.modules.identity.router import _session
    from fastapi import HTTPException
    row = SimpleNamespace(revoked_at=datetime.now(timezone.utc))
    session = MagicMock()
    session.scalar.return_value = row
    database = MagicMock()
    database.session.return_value.__enter__.return_value = session
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(database=database, settings=settings())))
    try:
        _session(request, "opaque-session")
        assert False
    except HTTPException as exc:
        assert exc.status_code == 401
    session.scalar.assert_called_once()
