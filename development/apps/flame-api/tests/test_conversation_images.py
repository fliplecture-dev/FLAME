from uuid import UUID, uuid4
from app.modules.functional.conversations.models import ConversationSession, Message
from app.modules.functional.resources.models import Resource
from app.modules.functional.identity.dependencies import require_admin
from test_curriculum_workspace import isolated_client


def test_owned_contextual_images_display_history_and_publication_rules():
    with isolated_client() as client:
        client.app.state.settings.resource_allowed_hosts = 'media.example.test'
        code = 'images-' + uuid4().hex[:10]
        c = client.post('/api/v1/admin/curricula', json={'code': code, 'name': 'Image fixture'}).json()
        def child(kind, parent, name):
            result = client.post('/api/v1/admin/curriculum/' + kind, json={'parent_id': parent, 'name': name})
            assert result.status_code == 201, result.text
            return result.json()['id']
        cid = c['id']; level = child('level', cid, 'Grade 1'); subject = child('subject', level, 'Science')
        domain = child('domain', subject, 'Motion'); topic = child('topic', domain, 'Force and Gravity'); leaf = child('subtopic', topic, 'Chapter 1')
        tree = client.get('/api/v1/admin/curricula/' + cid + '/tree').json()
        pub = client.post('/api/v1/admin/curriculum/curriculum/' + cid + '/publish', json={
            'expected_version': tree['version'], 'expected_draft_revision': tree['draft_revision']})
        assert pub.status_code == 200, pub.text
        revision = pub.json()['revision']; admin = client.app.dependency_overrides[require_admin]()['id']
        def resource(title, description, publish=True):
            response = client.post('/api/v1/admin/resources', json={'title': title, 'type': 'image', 'description': description,
                'external_url': 'https://media.example.test/' + uuid4().hex + '.png', 'alt_text': 'png', 'rights_basis': 'owned',
                'rights_holder': 'Fixture owner', 'distribution_scope': 'members', 'paths': [{'topic_id': topic, 'subtopic_id': leaf}]})
            assert response.status_code == 201, response.text
            row = response.json()
            if publish:
                response = client.post('/api/v1/admin/resources/' + row['id'] + '/publish', json={'expected_version': row['version']})
                assert response.status_code == 200, response.text
                row = response.json()
            return row
        force = resource('Force — push pull', 'Pushing a door and pulling a cart illustrate force.')
        gravity = resource('Gravity', 'Gravity pulls a falling ball towards Earth.')
        resource('Plants', 'A plant diagram explains photosynthesis.')
        resource('Gravity advanced', 'Grade 9 gravity equations.')
        resource('Gravity draft', 'Gravity pulls objects down.', publish=False)
        with client.app.state.database.session() as db, db.begin():
            conversation = ConversationSession(student_id=UUID(admin), mode='study', curriculum_id=UUID(cid), revision=revision,
                context_snapshot={'curriculum_id': cid, 'level_id': level, 'subject_id': subject, 'domain_id': domain,
                                  'category_id': None, 'topic_id': topic, 'subtopic_id': leaf})
            db.add(conversation); db.flush(); sid = str(conversation.id)
        number = 0
        def answer(question, explanation):
            nonlocal number
            number += 1
            with client.app.state.database.session() as db, db.begin():
                db.add(Message(session_id=UUID(sid), turn_number=number, role='user', blocks=[{'kind': 'text', 'text': question}]))
                response = Message(session_id=UUID(sid), turn_number=number, role='assistant', blocks=[{'kind': 'text', 'text': explanation}],
                    resolved_curriculum_id=UUID(cid), resolved_subject_id=UUID(subject), resolved_topic_id=UUID(topic), resolved_revision=revision)
                db.add(response); db.flush(); return str(response.id)
        def selection(mid):
            result = client.get('/api/v1/sessions/' + sid + '/recommendations', params={'message_id': mid})
            assert result.status_code == 200, result.text
            return result.json()
        def displayed(mid, row):
            return client.post('/api/v1/sessions/' + sid + '/images/displayed', json={
                'message_id': mid, 'resource_id': row['id'], 'resource_version': row['version']})
        first = answer('explain force', 'Force is a push or pull that can move a door.')
        decision = selection(first)
        assert decision['image_decision']['resource_id'] == force['id'] and decision['image_decision']['display_mode'] == 'inline'
        assert decision['resources'][0]['alt_text'] != 'png'
        assert displayed(first, gravity).status_code == 409
        assert displayed(first, force).status_code == 200
        follow = answer('another example', 'Force pushes a door or pulls a cart.')
        result = selection(follow)
        assert result['image_decision']['display_mode'] == 'reference earlier'
        assert result['image_decision']['reference_message_id'] == first
        new_concept = answer('explain gravity', 'Gravity is a force that pulls a falling ball down.')
        selected = selection(new_concept)
        assert selected['image_decision']['resource_id'] == gravity['id'] and selected['image_decision']['display_mode'] == 'inline'
        failed = client.post('/api/v1/sessions/' + sid + '/images/displayed', json={
            'message_id': new_concept, 'resource_id': gravity['id'], 'resource_version': gravity['version'], 'display_status': 'failed'})
        assert failed.status_code == 200, failed.text
        assert selection(new_concept)['image_decision'].get('failed') is True
        retry_answer = answer('explain gravity', 'Gravity pulls objects towards Earth.')
        assert selection(retry_answer)['image_decision']['display_mode'] == 'inline'
        assert displayed(retry_answer, gravity).status_code == 200
        assert displayed(new_concept, gravity).status_code == 200
        # A later failure must not erase a previously successful display.
        assert client.post('/api/v1/sessions/' + sid + '/images/displayed', json={
            'message_id': new_concept, 'resource_id': gravity['id'], 'resource_version': gravity['version'], 'display_status': 'failed'}).status_code == 200
        assert selection(new_concept)['image_decision']['displayed'] is True
        no_image = answer('explain evaporation', 'Water changes into gas during evaporation.')
        assert selection(no_image)['image_decision']['display_mode'] == 'none' and selection(no_image)['resources'] == []
        repeat = answer('show the force image again', 'Here is the force illustration.')
        assert selection(repeat)['image_decision']['display_mode'] == 'inline'
        # Reopening/repeating the GET preserves original decisions and successful-display history.
        assert selection(first)['image_decision']['displayed'] is True
        assert selection(follow)['image_decision']['display_mode'] == 'reference earlier'
        with client.app.state.database.session() as db, db.begin():
            row = db.get(Resource, UUID(force['id'])); row.published = False; row.version += 1
        unavailable = selection(first)
        assert unavailable['image_decision']['display_mode'] == 'none' and unavailable['resources'] == []
        assert displayed(first, force).status_code == 409
