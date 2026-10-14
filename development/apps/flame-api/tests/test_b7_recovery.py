"""Rollback-only terminal failure and interrupted worker recovery checks."""
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings
from app.main import create_app
from app.modules.conversations.models import AnswerRequest, Message
from app.modules.identity.dependencies import require_member
from app.modules.identity.models import StudentProfile
from app.modules.teaching.answer_service import ask
from app.modules.teaching.gateway import Generated, GatewayError
from app.modules.teaching.schemas import AnswerRequest as AskBody

pytestmark = pytest.mark.db_integration


@pytest.fixture
def owned_session():
    if os.environ.get('FLAME_RUN_DB_TESTS') != '1':
        pytest.skip('Set FLAME_RUN_DB_TESTS=1 for rollback-only database checks')
    settings = Settings()
    app = create_app(Settings(_env_file=None, environment='test', database_url=settings.database_url))
    member = uuid4()
    app.dependency_overrides[require_member] = lambda: {'id': str(member), 'role': 'member'}
    with TestClient(app) as client, app.state.database.engine.connect() as connection:
        outer = connection.begin()
        original = app.state.database.sessions
        app.state.database.sessions = sessionmaker(bind=connection, expire_on_commit=False,
                                                  join_transaction_mode='create_savepoint')
        try:
            with app.state.database.session() as db, db.begin():
                db.add(StudentProfile(id=member, auth_subject=str(member)))
            response = client.post('/api/v1/sessions', json={'mode': 'curiosity', 'context': None})
            assert response.status_code == 201, response.text
            yield app.state.database, member, UUID(response.json()['id'])
        finally:
            app.state.database.sessions = original
            outer.rollback()


class RecordingGateway:
    available = True

    def __init__(self, error=None):
        self.error = error
        self.prompts = []

    def generate(self, messages):
        self.prompts.append(messages)
        if self.error:
            raise self.error
        return Generated('Rainbows form when sunlight passes through water drops.', 'synthetic', 20, 10)


def test_terminal_timeout_replay_and_new_request(owned_session):
    database, member, sid = owned_session
    body = AskBody(mode='curiosity', question='How do rainbows form?')
    failed = RecordingGateway(GatewayError('provider_unavailable'))
    first = ask(database, failed, member, sid, 'timeout', body)
    assert first == {'status': 'error', 'code': 'provider_unavailable'}
    assert ask(database, failed, member, sid, 'timeout', body) == first
    assert len(failed.prompts) == 1
    with database.session() as db:
        assert db.query(Message).filter_by(session_id=sid).count() == 0
        row = db.query(AnswerRequest).filter_by(session_id=sid).one()
        assert row.status == 'failed' and row.claim_token is None and row.lease_expires_at is None
    success = RecordingGateway()
    result = ask(database, success, member, sid, 'new-attempt', body)
    assert result['status'] == 'ok'
    assert ask(database, success, member, sid, 'new-attempt', body) == result
    assert len(success.prompts) == 1
    with database.session() as db:
        assert db.query(Message).filter_by(session_id=sid).count() == 2


def test_interrupted_worker_recovers_after_lease_without_duplicate_turns(owned_session):
    database, member, sid = owned_session
    body = AskBody(mode='curiosity', question='How do rainbows form?')

    class WorkerInterrupted(BaseException):
        pass

    with pytest.raises(WorkerInterrupted):
        ask(database, RecordingGateway(WorkerInterrupted()), member, sid, 'interrupted', body)
    with database.session() as db, db.begin():
        row = db.query(AnswerRequest).filter_by(session_id=sid).one()
        assert row.status == 'pending' and row.attempts == 1
        row.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    gateway = RecordingGateway()
    first = ask(database, gateway, member, sid, 'interrupted', body)
    assert first['status'] == 'ok'
    assert ask(database, gateway, member, sid, 'interrupted', body) == first
    follow_up = AskBody(mode='curiosity', question='Why can we see different colours?')
    assert ask(database, gateway, member, sid, 'follow-up', follow_up)['status'] == 'ok'
    assert any(message['role'] == 'user' and body.question in message['content']
               for message in gateway.prompts[1][:-1])
    assert any(message['role'] == 'assistant' and 'water drops' in message['content']
               for message in gateway.prompts[1][:-1])
    with database.session() as db:
        assert db.query(Message).filter_by(session_id=sid).count() == 4
        row = db.query(AnswerRequest).filter_by(session_id=sid, idempotency_key='interrupted').one()
        assert row.status == 'completed' and row.attempts == 2
        assert row.claim_token is None and row.lease_expires_at is None
