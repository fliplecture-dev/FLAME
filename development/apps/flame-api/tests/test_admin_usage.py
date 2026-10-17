import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.modules.functional.identity.dependencies import require_member
from app.modules.functional.identity.models import StudentProfile
from app.modules.application.teaching import answer_router
from app.modules.application.teaching import simulation_router
from app.modules.application.teaching.gateway import Generated
from app.modules.application.teaching.schemas import AnswerRequest
from app.modules.application.teaching.simulations import TransientSimulations
from app.modules.application.teaching.usage import daily_usage_limit


@pytest.mark.parametrize("role,expected", [("admin", None), ("member", 25), (None, 25)])
@pytest.mark.parametrize("mode", ["study", "curiosity"])
def test_complete_and_streamed_answers_use_verified_role_quota(monkeypatch, role, expected, mode):
    assert daily_usage_limit({"role": role}, 100) == expected
    monkeypatch.setattr(answer_router, "owned", lambda *args: None)
    limits = []
    def generated(*args, **kwargs):
        limits.append(kwargs["daily_limit"])
        return {"status": "ok"}
    monkeypatch.setattr(answer_router, "ask", generated)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        database=MagicMock(), gateway=MagicMock(), settings=SimpleNamespace(llm_daily_request_limit=100))))
    context = {name: str(uuid4()) for name in ["curriculum_id", "level_id", "subject_id", "domain_id", "topic_id"]} if mode == "study" else None
    body = AnswerRequest(question="Hello", mode=mode, context=context)
    principal = {"id": str(uuid4()), "role": role}
    assert answer_router.ask_question(request, uuid4(), body, principal, "complete")["status"] == "ok"
    response = answer_router.ask_stream(request, uuid4(), body, principal, "stream")
    async def collect():
        return [json.loads(chunk) async for chunk in response.body_iterator]
    assert asyncio.run(collect())[-1]["answer"]["status"] == "ok"
    assert limits == [expected, expected]


def test_unlimited_simulation_usage_preserves_member_cap_and_capacity():
    store = TransientSimulations()
    factory = lambda: {"source": "fixture"}
    for i in range(25):
        assert store.run("admin", str(i), factory, start=True, limit=None)["status"] == "ready"
    assert store.run("member", "one", factory, start=True, limit=1)["status"] == "ready"
    assert store.run("member", "two", lambda: pytest.fail("member quota bypassed"), start=True, limit=1)["status"] == "limited"
    bounded = TransientSimulations(maximum=1)
    assert bounded.run("admin", "one", factory, start=True, limit=None)["status"] == "ready"
    assert bounded.run("admin", "two", factory, start=True, limit=None)["status"] == "limited"


@pytest.mark.parametrize("role,expected", [("admin", None), ("member", 20)])
def test_simulation_route_uses_verified_role_quota(monkeypatch, role, expected):
    database = MagicMock()
    database.session.return_value.__enter__.return_value.scalar.side_effect = [
        SimpleNamespace(turn_number=1), SimpleNamespace(blocks=[{"text": "Interactive falling ball"}]), None]
    monkeypatch.setattr(simulation_router, "owned", lambda *args, **kw: SimpleNamespace(mode="curiosity"))
    monkeypatch.setattr(simulation_router, "library_simulation", lambda *args, **kw: (None, None))
    transient = MagicMock()
    transient.run.return_value = {"status": "pending"}
    monkeypatch.setattr(simulation_router, "transient", transient)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
        database=database, gateway=SimpleNamespace(available=True),
        settings=SimpleNamespace(llm_daily_request_limit=100))))
    simulation_router.simulation(request, uuid4(),
        simulation_router.SimulationRequest(message_id=uuid4(), start=True),
        {"id": str(uuid4()), "role": role})
    assert transient.run.call_args.kwargs["limit"] == expected


@pytest.mark.db_integration
def test_admin_can_ask_beyond_member_limit_but_member_still_cannot():
    if os.environ.get("FLAME_RUN_DB_TESTS") != "1":
        pytest.skip("Set FLAME_RUN_DB_TESTS=1 for rollback-only database checks")
    settings = Settings()
    app = create_app(Settings(_env_file=None, environment="test", database_url=settings.database_url,
                              llm_daily_request_limit=1))
    member = uuid4()
    role = {"id": str(member), "role": "admin"}
    app.dependency_overrides[require_member] = lambda: role
    class Gateway:
        available = True
        calls = 0
        def generate(self, messages):
            self.calls += 1
            return Generated("Gravity pulls objects toward Earth.", "fixture", 10, 8)
    with TestClient(app) as client:
        gateway = Gateway()
        app.state.gateway = gateway
        with app.state.database.engine.connect() as connection:
            transaction = connection.begin()
            original = app.state.database.sessions
            app.state.database.sessions = sessionmaker(bind=connection, expire_on_commit=False,
                                                        join_transaction_mode="create_savepoint")
            try:
                with app.state.database.session() as db, db.begin():
                    db.add(StudentProfile(id=member, auth_subject=str(uuid4()), status="active"))
                created = client.post("/api/v1/sessions", json={"mode": "curiosity"})
                assert created.status_code == 201
                route = "/api/v1/sessions/" + created.json()["id"] + "/ask"
                body = {"question": "Explain gravity", "mode": "curiosity"}
                first = client.post(route, json=body, headers={"Idempotency-Key": "first"})
                second = client.post(route, json=body, headers={"Idempotency-Key": "second"})
                assert first.status_code == second.status_code == 200
                assert gateway.calls == 2
                role["role"] = "member"
                replay = client.post(route, json=body, headers={"Idempotency-Key": "first"})
                assert replay.json()["message_id"] == first.json()["message_id"]
                denied = client.post(route, json=body, headers={"Idempotency-Key": "third"})
                assert denied.status_code == 429 and denied.json()["error"]["code"] == "daily_limit_reached"
                assert gateway.calls == 2
            finally:
                app.state.database.sessions = original
                transaction.rollback()
