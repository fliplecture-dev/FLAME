from types import SimpleNamespace
from app.modules.decision_engine.recommendation.image_selection import decide_image, description


def image(id, title, **kwargs):
    return SimpleNamespace(id=id, title=title, description=kwargs.get('description', title), alt_text=kwargs.get('alt_text', 'png'),
        caption_or_transcript=None, accessibility_note=None, type='image', published=kwargs.get('published', True),
        availability=kwargs.get('availability', 'available'), version=kwargs.get('version', 2))


def test_concept_match_is_mandatory_and_grade_is_checked():
    force = image('force', 'Force — push pull')
    gravity = image('gravity', 'Gravity makes objects fall')
    assert decide_image([force], 'explain gravity', 'Gravity is a force that pulls objects down.')['display_mode'] == 'none'
    assert decide_image([gravity, force], 'explain force', 'Force is a push or pull.')['resource_id'] == 'force'
    assert decide_image([force, gravity], 'explain gravity', 'Gravity is a force that pulls objects down.')['resource_id'] == 'gravity'
    assert decide_image([image('advanced', 'Grade 9 gravity equations')], 'explain gravity', 'Gravity pulls objects down.', grade='Grade 1')['display_mode'] == 'none'
    assert decide_image([force], 'explain force', 'This answer teaches photosynthesis.')['display_mode'] == 'none'
    assert decide_image([image('draft', 'Force', published=False), image('offline', 'Force', availability='unavailable')], 'explain force', 'Force is a push.')['display_mode'] == 'none'


def test_displayed_versions_repeat_requests_and_failed_loads():
    force = image('force', 'Force — push pull')
    first = decide_image([force], 'explain force', 'Force is a push or pull.')
    history = [{**first, 'message_id': 'first-answer', 'displayed': True}]
    follow = decide_image([force], 'another example', 'Force pushes a door.', previous_question='explain force', history=history)
    assert follow['display_mode'] == 'reference earlier' and follow['reference_message_id'] == 'first-answer'
    assert decide_image([force], 'show the force image again', 'Here is the force illustration.', history=history)['display_mode'] == 'inline'
    assert decide_image([force], 'show the image again', 'Here is the picture.', previous_question='explain force', history=history)['display_mode'] == 'inline'
    assert decide_image([image('force', 'Force — push pull', version=3)], 'explain force', 'Force pushes a door.', history=history)['display_mode'] == 'inline'
    assert decide_image([force], 'explain force', 'Force pushes a door.', history=[{**first, 'displayed': False}])['display_mode'] == 'none'
    assert decide_image([force], 'explain force', 'Force pushes a door.', history=[{**first, 'displayed': False, 'failed': True}])['display_mode'] == 'inline'
    assert description(force)[0] == 'Force — push pull'


def test_question_concept_wins_over_generic_answer_and_association_objective():
    force = image('force', 'Force — push pull')
    result = decide_image([force], 'explain gravity', 'Gravity is a force. A force can push and pull.', objective='Explain force and gravity.', subtopic_ids={'force'})
    assert result['resource_id'] is None and result['display_mode'] == 'none'
