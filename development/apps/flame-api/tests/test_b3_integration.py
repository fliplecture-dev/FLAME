"""Rollback-only B3 session and access checks against migrated development PostgreSQL."""
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

import jwt
import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.modules.functional.identity.dependencies import require_admin, require_member, require_owner
from app.modules.functional.identity.models import AdminRole, BrowserSession

pytestmark = pytest.mark.db_integration
ISSUER = "https://b3-test.supabase.co/auth/v1"
SECRET = "b3-test-signing-key"


def signed(subject):
    now = datetime.now(timezone.utc)
    return jwt.encode({
        "iss": ISSUER, "aud": "authenticated", "sub": str(subject),
        "role": "authenticated", "email": str(subject) + "@example.test",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=10)).timestamp()),
        "user_metadata": {"display_name": "Test member"},
    }, SECRET, algorithm="HS256")


def test_session_profile_admin_owner_refresh_and_logout_rollback_only():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for rollback-only B3 database tests")
    existing = Settings()
    assert existing.database_url and existing.session_encryption_key
    app = create_app(Settings(
        _env_file=None, environment="test", database_url=existing.database_url,
        session_encryption_key=existing.session_encryption_key,
        supabase_url="https://b3-test.supabase.co",
        supabase_anon_key="test-key", supabase_jwt_secret=SECRET,
        bff_shared_key="test-bff-secret"))

    @app.get("/test/owned/{student_id}")
    def owned(student_id: str, principal: dict = Depends(require_member)):
        from uuid import UUID
        require_owner(principal, UUID(student_id))
        return {"status": "owned"}

    @app.get("/test/admin")
    def admin_only(principal: dict = Depends(require_admin)):
        return {"status": "admin"}

    headers = {"x-bff-key": "test-bff-secret"}
    with TestClient(app) as client:
        with app.state.database.engine.connect() as connection:
            outer = connection.begin()
            original = app.state.database.sessions
            app.state.database.sessions = sessionmaker(
                bind=connection, expire_on_commit=False, join_transaction_mode="create_savepoint")
            try:
                first, second = uuid4(), uuid4()
                with patch("app.modules.functional.identity.router._provider", side_effect=[
                    {"access_token": signed(first), "refresh_token": "refresh-one"},
                    {"email_confirmed_at": "2026-09-26T00:00:00Z"},
                ]):
                    login = client.post("/api/v1/auth/login", headers=headers,
                                        json={"email": "one@example.test", "password": "test-password"})
                assert login.status_code == 200, login.text
                opaque = login.json()["session"]
                own_headers = {**headers, "x-flame-session": opaque}
                me = client.get("/api/v1/me", headers=own_headers)
                assert me.status_code == 200, me.text
                student_id = me.json()["id"]
                assert me.json()["role"] == "member"
                assert client.get("/test/owned/" + student_id, headers=own_headers).status_code == 200

                with app.state.database.session() as session, session.begin():
                    session.add(AdminRole(auth_subject=str(first)))
                assert client.get("/api/v1/me", headers=own_headers).json()["role"] == "admin"

                with patch("app.modules.functional.identity.router._provider", side_effect=[
                    {"access_token": signed(second), "refresh_token": "refresh-two"},
                    {"email_confirmed_at": "2026-09-26T00:00:00Z"},
                ]):
                    other = client.post("/api/v1/auth/login", headers=headers,
                                        json={"email": "two@example.test", "password": "test-password"})
                other_headers = {**headers, "x-flame-session": other.json()["session"]}
                assert client.get("/test/admin", headers=own_headers).status_code == 200
                assert client.get("/test/admin", headers=other_headers).status_code == 403
                assert client.get("/test/owned/" + student_id, headers=other_headers).status_code == 404
                with app.state.database.session() as session, session.begin():
                    other_row = session.scalar(select(BrowserSession).where(BrowserSession.auth_subject == str(second)))
                    other_row.created_at = datetime.now(timezone.utc) - timedelta(days=8)
                assert client.get("/api/v1/me", headers=other_headers).status_code == 401

                with app.state.database.session() as session, session.begin():
                    row = session.scalar(select(BrowserSession).where(BrowserSession.auth_subject == str(first)))
                    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                with patch("app.modules.functional.identity.router._provider", return_value={
                    "access_token": signed(first), "refresh_token": "rotated-refresh",
                }):
                    assert client.get("/api/v1/me", headers=own_headers).status_code == 200
                with patch("app.modules.functional.identity.router._provider", return_value={}):
                    assert client.post("/api/v1/auth/logout", headers=own_headers).status_code == 200
                assert client.get("/api/v1/me", headers=own_headers).status_code == 401
            finally:
                app.state.database.sessions = original
                outer.rollback()


def test_direct_client_role_cannot_read_flame_profiles():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for migrated database access checks")
    from app.core.database import Database
    database = Database(Settings())
    try:
        with database.engine.connect() as connection:
            with connection.begin():
                connection.execute(text("SET LOCAL ROLE authenticated"))
                with pytest.raises(DBAPIError):
                    connection.execute(text("SELECT 1 FROM flame.student_profiles LIMIT 0"))
    finally:
        database.close()
