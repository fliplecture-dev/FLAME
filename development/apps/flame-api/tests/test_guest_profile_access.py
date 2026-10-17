"""Hermetic SQL/HTTP access-policy checks; no Supabase or paid provider calls.

SQLite exercises ownership, persistence and limits. PostgreSQL locking/RLS remain
separate database-integration acceptance checks.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from types import SimpleNamespace
from uuid import UUID, uuid4
import importlib.util
import io

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine, JSON, MetaData, select, text, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.config import Settings
from app.core.database import Base
from app.main import create_app
from app.modules.functional.identity.dependencies import require_member
from app.modules.functional.identity.models import GuestAccess, StudentProfile
from app.modules.functional.identity.profile_data import ProfileEdit
from app.modules.functional.identity.router import LoginBody, RegisterBody
from app.modules.functional.conversations.models import AnswerRequest
from app.modules.application.teaching.gateway import Generated
from app.modules.application.teaching.usage import quota_day_start, daily_usage_limit

KEY = {"x-bff-key": "access-test-secret"}


@pytest.fixture
def database():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    metadata = MetaData(naming_convention=Base.metadata.naming_convention)
    for table in Base.metadata.tables.values():
        clone = table.to_metadata(metadata)
        for column in clone.columns:
            if isinstance(column.type, JSONB):
                column.type = JSON()
    names = ["student_profiles", "guest_access", "sessions", "messages", "answer_requests", "activity_events"]
    # Activity's actual table name is stable but explicit in the owner declaration.
    from app.modules.functional.student_activity.models import ActivityEvent
    names[-1] = ActivityEvent.__tablename__
    with engine.begin() as conn:
        conn.execute(text("ATTACH DATABASE ':memory:' AS flame"))
        metadata.create_all(conn, tables=[metadata.tables["flame." + name] for name in names])
    @contextmanager
    def session():
        with Session(engine, expire_on_commit=False) as db:
            yield db
    yield SimpleNamespace(session=session, close=lambda: None)
    engine.dispose()


@pytest.fixture
def api(database):
    app = create_app(Settings(_env_file=None, environment="test", database_url=None, bff_shared_key="access-test-secret"))
    calls = []
    class Gateway:
        available = True
        def generate(self, messages):
            calls.append(messages)
            return Generated("The sky looks blue because air scatters blue light more strongly.", "synthetic", 8, 12)
    with TestClient(app) as client:
        app.state.database = database
        app.state.gateway = Gateway()
        yield client, app, calls


def guest(client):
    created = client.post("/api/v1/guest/identity", headers=KEY)
    assert created.status_code == 201, created.text
    token = created.json()["token"]
    headers = {**KEY, "x-flame-guest": token}
    row = client.post("/api/v1/guest/sessions", headers=headers, json={"mode": "curiosity", "context": None})
    assert row.status_code == 201, row.text
    return headers, row.json()["id"]


def test_calendar_reset_is_midnight_india_time_and_fixed_limits():
    before = datetime(2026,10,17,18,29,59,tzinfo=timezone.utc)
    after = before+timedelta(seconds=1)
    assert quota_day_start(before) == datetime(2026,10,16,18,30,tzinfo=timezone.utc)
    assert quota_day_start(after) == datetime(2026,10,17,18,30,tzinfo=timezone.utc)
    assert daily_usage_limit({"role":"guest"},100) == 10
    assert daily_usage_limit({"role":"member"},100) == 25
    assert daily_usage_limit({"role":"member"},5) == 5
    assert daily_usage_limit({"role":"admin"},25) is None


def test_guest_10_questions_same_key_replay_and_calendar_day_count(api, database):
    client, app, calls = api
    headers, sid = guest(client)
    body = {"mode":"curiosity","context":None,"question":"Why is the sky blue?"}
    for index in range(10):
        response = client.post(f"/api/v1/guest/sessions/{sid}/ask",headers={**headers,"Idempotency-Key":str(index)},json=body)
        assert response.status_code == 200, response.text
    assert len(calls) == 10
    over = client.post(f"/api/v1/guest/sessions/{sid}/ask",headers={**headers,"Idempotency-Key":"over"},json=body)
    assert over.status_code == 429
    assert over.json()["error"]["code"] == "daily_limit_reached"
    stream = client.post(f"/api/v1/guest/sessions/{sid}/ask-stream",headers={**headers,"Idempotency-Key":"over-stream"},json=body)
    assert stream.status_code == 200
    assert any(json.loads(line).get("code")=="daily_limit_reached" for line in stream.text.splitlines())
    assert client.post("/api/v1/guest/sessions",headers=headers,json={"mode":"curiosity"}).json()["id"] == sid
    replay = client.post(f"/api/v1/guest/sessions/{sid}/ask",headers={**headers,"Idempotency-Key":"0"},json=body)
    assert replay.status_code == 200 and len(calls) == 10
    usage = client.get("/api/v1/guest/usage",headers=headers).json()
    assert (usage["used"],usage["limit"],usage["remaining"],usage["timezone"]) == (10,10,0,"Asia/Kolkata")
    # Earlier today at UTC can belong to the previous India calendar day.
    with database.session() as db, db.begin():
        first = db.scalar(select(AnswerRequest).where(AnswerRequest.idempotency_key=="0"))
        first.created_at = quota_day_start()-timedelta(seconds=1)
    assert client.get("/api/v1/guest/usage",headers=headers).json()["remaining"] == 1
    allowed = client.post(f"/api/v1/guest/sessions/{sid}/ask",headers={**headers,"Idempotency-Key":"new-day-slot"},json=body)
    assert allowed.status_code == 200 and len(calls) == 11


def test_guest_capability_is_private_expiring_and_cannot_use_study_or_member_routes(api,database):
    client,app,calls = api
    h1,sid1 = guest(client);h2,sid2 = guest(client)
    assert sid1 != sid2
    assert client.post("/api/v1/guest/sessions",headers=h1,json={"mode":"study","context":{}}).status_code == 422
    assert client.post(f"/api/v1/guest/sessions/{sid1}/ask",headers={**h1,"Idempotency-Key":"study"},json={"mode":"study","context":None,"question":"Explain"}).status_code == 422
    assert client.post(f"/api/v1/guest/sessions/{sid1}/ask",headers={**h2,"Idempotency-Key":"foreign"},json={"mode":"curiosity","question":"Explain"}).status_code == 404
    for path in ["/api/v1/me/profile","/api/v1/sessions","/api/v1/admin/students"]:
        assert client.get(path,headers=h1).status_code in (401,403)
    assert client.post("/api/v1/guest/identity").status_code == 403
    assert not calls
    raw = h1["x-flame-guest"]
    with database.session() as db,db.begin():
        access = db.get(GuestAccess,sha256(raw.encode()).hexdigest())
        assert access and access.id_hash != raw
        access.expires_at = datetime.now(timezone.utc)-timedelta(seconds=1)
    assert client.get("/api/v1/guest/me",headers=h1).status_code == 401
    assert client.get("/api/v1/guest/me",headers={**KEY,"x-flame-guest":"invented"}).status_code == 401


def member(app,database):
    pid = uuid4()
    with database.session() as db,db.begin():
        db.add(StudentProfile(id=pid,auth_subject=str(uuid4()),status="active",email="student@example.test",display_name="Student"))
    principal={"id":str(pid),"role":"member"}
    app.dependency_overrides[require_member]=lambda:principal
    return principal


def test_signed_in_limit_25_and_duplicate_does_not_use_an_extra_question(api,database):
    client,app,calls=api
    principal=member(app,database)
    sid=client.post("/api/v1/sessions",json={"mode":"curiosity","context":None}).json()["id"]
    body={"mode":"curiosity","question":"Why is the sky blue?"}
    for index in range(25):
        result=client.post(f"/api/v1/sessions/{sid}/ask",headers={"Idempotency-Key":str(index)},json=body)
        assert result.status_code==200,result.text
    assert client.post(f"/api/v1/sessions/{sid}/ask",headers={"Idempotency-Key":"26"},json=body).status_code==429
    assert client.post(f"/api/v1/sessions/{sid}/ask",headers={"Idempotency-Key":"0"},json=body).status_code==200
    other=client.post("/api/v1/sessions",json={"mode":"curiosity","context":None}).json()["id"]
    assert client.post(f"/api/v1/sessions/{other}/ask",headers={"Idempotency-Key":"cross-session"},json=body).status_code==429
    assert len(calls)==25
    assert client.get("/api/v1/me/usage").json()["remaining"]==0


def test_profile_update_is_owned_optional_clearable_and_rejects_privilege_changes(api,database):
    client,app,calls=api
    first=member(app,database)
    details={"display_name":"Learner","phone_number":"+91 98765 43210","contact_number":"044 2345 6789","address":"12 Learning Road","city":"Chennai","state":"Tamil Nadu","country":"India","pincode":"600001"}
    saved=client.patch("/api/v1/me/profile",json=details)
    assert saved.status_code==200,saved.text
    assert saved.json()=={**details,"email":"student@example.test"}
    assert client.get("/api/v1/me/profile").json()["address"]==details["address"]
    for payload in [{"role":"admin"},{"auth_subject":"other"},{"email":"other@example.test"},{"student_id":str(uuid4())},{"phone_number":"invalid"}]:
        assert client.patch("/api/v1/me/profile",json=payload).status_code==422
    assert client.patch("/api/v1/me/profile",json={"phone_number":"","address":" "}).json()["phone_number"] is None
    other=member(app,database)
    assert client.get("/api/v1/me/profile").json()["city"] is None
    app.dependency_overrides.clear()
    assert client.get("/api/v1/me/profile",headers=KEY).status_code==401
    assert not calls


def test_optional_auth_phone_is_validated_and_registration_preserves_it(api,monkeypatch):
    client,app,calls=api
    assert LoginBody(email="x@example.test",password="secret").phone_number is None
    assert LoginBody(email="x@example.test",password=" secret ").password == " secret "
    assert RegisterBody(email="x@example.test",password="long-password",display_name="X").phone_number is None
    for phone in ["abc","123", "9"*16]:
        with pytest.raises(ValidationError):LoginBody(email="x@example.test",password="secret",phone_number=phone)
    provider=[]
    def fake(*args,**kwargs):provider.append(kwargs["body"]);return {}
    monkeypatch.setattr("app.modules.functional.identity.router._provider",fake)
    result=client.post("/api/v1/auth/register",headers=KEY,json={"email":"x@example.test","password":"long-password","display_name":"X","phone_number":"+91 98765 43210"})
    assert result.status_code==200
    assert provider[0]["data"]["phone_number"]=="+91 98765 43210"


def test_migration_source_renders_profile_columns_guest_fk_and_rls():
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    spec=importlib.util.spec_from_file_location("access_migration",Path(__file__).resolve().parents[1]/"migrations/versions/20261017_32_guest_access_profiles.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    output=io.StringIO();module.op=Operations(MigrationContext.configure(dialect_name="postgresql",opts={"as_sql":True,"output_buffer":output}))
    module.upgrade();ddl=output.getvalue()
    assert "guest_access" in ddl and "ENABLE ROW LEVEL SECURITY" in ddl
    for name,_ in module.FIELDS:assert name in ddl


def test_optional_login_phone_is_saved_only_to_the_authenticated_profile(api,database,monkeypatch):
    client,app,calls=api
    principal=member(app,database)
    def provider(settings,method,path,**kwargs):
        return {"email_confirmed_at":"2026-10-17"} if path=="/user" else {"access_token":"verified","refresh_token":"refresh"}
    monkeypatch.setattr("app.modules.functional.identity.router._provider",provider)
    monkeypatch.setattr("app.modules.functional.identity.router._store",lambda *args:"opaque-session")
    monkeypatch.setattr("app.modules.functional.identity.router._principal",lambda *args:principal)
    result=client.post("/api/v1/auth/login",headers=KEY,json={"email":"student@example.test","password":"password","phone_number":"+91 98765 43210"})
    assert result.status_code==200,result.text
    with database.session() as db:
        assert db.get(StudentProfile,UUID(principal["id"])).phone_number=="+91 98765 43210"
