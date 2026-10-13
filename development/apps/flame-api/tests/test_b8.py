"""B8 capability and complete-block validation checks."""
from uuid import uuid4
import pytest
from pydantic import ValidationError
from app.modules.teaching.capabilities import unsupported_capability
from app.modules.teaching.schemas import DirectAnswer, UnsupportedOutcome
from app.modules.teaching.answer_service import _answer
from app.modules.teaching.context import TeachingContext
from app.modules.teaching.gateway import Generated, GatewayError

@pytest.mark.parametrize('question,code', [
    ('Please cite the textbook page for this answer.', 'textbook_evidence_unavailable'),
    ('Grade my answer to this question.', 'official_grading_unavailable'),
    ('Read this uploaded PDF for me.', 'student_file_understanding_unavailable'),
    ('Watch this video and explain it.', 'media_understanding_unavailable'),
    ('Update my mastery score.', 'progress_update_unavailable'),
])
def test_explicit_unsupported_capability(question, code):
    result = unsupported_capability(question)
    assert result and result.code == code
    assert UnsupportedOutcome(request_id=uuid4(), code=result.code, message=result.message).status == 'unsupported'

@pytest.mark.parametrize('question', [
    'What is an image?', 'How does a video camera work?',
    'What does grade 5 mean?', 'Why does a ball fall?',
])
def test_ordinary_school_questions_are_not_blocked(question):
    assert unsupported_capability(question) is None


def test_answer_blocks_require_unique_ids_and_bounded_content():
    values = dict(response_id=uuid4(), request_id=uuid4(), curriculum_version='revision-1')
    with pytest.raises(ValidationError):
        DirectAnswer(**values, blocks=[{'id': 'a', 'kind': 'text', 'text': ' ' }])
    with pytest.raises(ValidationError):
        DirectAnswer(**values, blocks=[{'id': 'a', 'kind': 'text', 'text': 'First'},
                                       {'id': 'a', 'kind': 'text', 'text': 'Second'}])
    with pytest.raises(ValidationError):
        DirectAnswer(**values, blocks=[{'id': 'a', 'kind': 'list', 'items': ['x' * 501]}])
    context = TeachingContext(ids={}, names={}, revision=1, curriculum_description=None, learning_outcome=None)
    with pytest.raises(GatewayError) as error:
        _answer(uuid4(), context, Generated('Unsafe\x00control', 'stub', 1, 1))
    assert error.value.code == 'invalid_provider_output'


@pytest.mark.parametrize('text', [
    'According to the textbook, this is true.',
    'I checked your uploaded file and found the answer.',
    'Your official grade is 90%.',
    'See https://example.test for proof.',
])
def test_direct_model_text_cannot_claim_unverified_authority(text):
    context = TeachingContext(ids={}, names={}, revision=1, curriculum_description=None, learning_outcome=None)
    with pytest.raises(GatewayError) as error:
        _answer(uuid4(), context, Generated(text, 'stub', 10, 10))
    assert error.value.code == 'invalid_provider_output'


def test_plain_explanation_and_honest_boundary_remain_valid():
    context = TeachingContext(ids={}, names={}, revision=1, curriculum_description=None, learning_outcome=None)
    for text in ('Earth pulls the ball downward.', 'I cannot read your file; ask a text question instead.'):
        assert _answer(uuid4(), context, Generated(text, 'stub', 10, 10))['status'] == 'ok'


def test_study_answer_enforces_profile_word_limit_without_changing_open_curiosity():
    context = TeachingContext(ids={}, names={}, revision=1, curriculum_description=None, learning_outcome=None)
    text = "word " * 61
    with pytest.raises(GatewayError) as error:
        _answer(uuid4(), context, Generated(text, "stub", 10, 10), max_words=60)
    assert error.value.code == "invalid_provider_output"
    assert _answer(uuid4(), None, Generated(text, "stub", 10, 10))["status"] == "ok"
