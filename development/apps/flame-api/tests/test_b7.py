from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from app.core.config import Settings
from app.main import create_app
from app.modules.identity.dependencies import require_member
from app.modules.teaching.answer_service import _answer
from app.modules.teaching.context import TeachingContext
from app.modules.teaching.gateway import Generated, GatewayError
from app.modules.teaching.schemas import DirectAnswer


def test_provider_text_cannot_assign_provenance():
    context = TeachingContext(ids={}, names={}, revision=7, curriculum_description=None, learning_outcome=None)
    answer = DirectAnswer.model_validate(_answer(uuid4(), context, Generated(' Gravity pulls. ', 'stub', 12, 6)))
    assert answer.blocks[0].text == 'Gravity pulls.'
    assert answer.curriculum_version == 'revision-7'
    assert answer.route == 'direct_llm' and answer.knowledge_source == 'model_generated'
    assert answer.grounded is False and answer.confidence is None
    assert answer.citations == [] and answer.resources == []
    with pytest.raises(GatewayError):
        _answer(uuid4(), context, Generated(' ', 'stub', 0, 0))
    with pytest.raises(GatewayError):
        _answer(uuid4(), context, Generated('x' * 6001, 'stub', 0, 0))


def test_unconfigured_provider_rejects_before_database_claim():
    app = create_app(Settings(_env_file=None, environment='test'))
    app.dependency_overrides[require_member] = lambda: {'id': str(uuid4()), 'role': 'member'}
    with TestClient(app) as client:
        response = client.post(f'/api/v1/sessions/{uuid4()}/ask', headers={'Idempotency-Key': 'first'},
            json={'mode': 'curiosity', 'context': None, 'question': 'Why?'})
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'provider_unavailable'


def test_open_curiosity_answer_has_no_curriculum_claim():
    answer = DirectAnswer.model_validate(_answer(uuid4(), None,
        Generated('Fractions are parts of a whole.', 'stub', 20, 10)))
    assert answer.curriculum_version is None
    assert answer.grounded is False and answer.citations == []
