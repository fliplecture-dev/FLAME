"""HTTP regression for draft replacement concurrency. All DB writes roll back."""
import os
from io import BytesIO
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.main import create_app
from app.modules.functional.identity.dependencies import require_admin, require_member
from app.modules.functional.identity.models import AdminRole, StudentProfile
pytestmark = pytest.mark.db_integration

def test_replacement_revision_recovery():
    if os.getenv('FLAME_RUN_DB_TESTS') != '1': pytest.skip('Enable database integration tests')
    app = create_app(Settings(_env_file=None, environment='test', database_url=Settings().database_url))
    admin = uuid4(); principal = {'id': str(admin), 'role': 'admin'}
    app.dependency_overrides[require_admin] = lambda: principal
    app.dependency_overrides[require_member] = lambda: principal
    with TestClient(app) as client, app.state.database.engine.connect() as connection:
        outer = connection.begin(); original = app.state.database.sessions
        app.state.database.sessions = sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint')
        try:
            with app.state.database.session() as session, session.begin():
                session.add_all([StudentProfile(id=admin, auth_subject=str(admin)), AdminRole(auth_subject=str(admin))])
            code = 'replacement-' + uuid4().hex[:10]
            c = client.post('/api/v1/admin/curricula', json={'code': code, 'name': 'Replacement test'}).json()
            cid = c['id']; root = '/api/v1/admin/curricula/' + cid; imports = '/api/v1/admin/curriculum/imports'
            def tree(): return client.get(root + '/tree').json()
            def upload(payload):
                r = client.post(imports, params={'curriculum_id': cid}, files={'file': ('test.xlsx', payload)})
                assert r.status_code == 201, r.text
                return r.json()['import_id']
            def preview(i):
                r = client.post(imports + '/' + i + '/preview', json={'sheet_levels': {'Curriculum': '__ALL_LEVELS__'}})
                assert r.status_code == 200, r.text
                return r.json()
            def commit(i, p, key=None):
                return client.post(imports + '/' + i + '/commit', headers={'idempotency-key': key or uuid4().hex},
                    json={'preview_revision': p['preview_revision'], 'confirm': 'REPLACE ' + code})
            def publish():
                t = tree(); r = client.post('/api/v1/admin/curriculum/curriculum/' + cid + '/publish',
                    json={'expected_version': t['version'], 'expected_draft_revision': t['draft_revision']})
                assert r.status_code == 200, r.text
            tree()
            wb = Workbook(); sh = wb.active; sh.title = 'Curriculum'
            sh.append(['Curriculum Code', 'Level', 'Subject', 'Domain', 'Category', 'Topic', 'Subtopic', 'Learning Outcome', 'Source URL'])
            sh.append([code, 'Grade 1', 'Science', 'Motion', None, 'Push', 'Basics'])
            out = BytesIO(); wb.save(out)
            first = upload(out.getvalue()); p = preview(first); key = uuid4().hex
            r = commit(first, p, key); assert r.status_code == 200, r.text
            assert commit(first, p, key).json() == r.json()
            assert tree()['published_revision'] == 0
            publish()
            exported = client.get(root + '/export', params={'source': 'published'})
            assert exported.status_code == 200
            second = upload(exported.content)
            detail = client.get(imports + '/' + second).json()
            assert detail['round_trip'] and detail['metadata']['curriculum_id'] == cid
            p2 = preview(second)
            assert p2['counts']['created'] == p2['counts']['removed'] == 0
            assert p2['counts']['reused'] == 1
            assert commit(second, p2).status_code == 200
            third = upload(exported.content); p3 = preview(third)
            assert third != second and p3['preview_revision'] != p2['preview_revision']
            t = tree(); sub = t['levels'][0]['subjects'][0]['domains'][0]['topics'][0]['subtopics'][0]
            edit = client.post(root + '/paths/batch', json={'expected_revision': t['draft_revision'], 'changes': [{
                'key': sub['id'], 'source_subtopic_id': sub['id'], 'action': 'upsert', 'values': {
                    'level': 'Grade 1', 'subject': 'Science', 'domain': 'Motion', 'category': '', 'topic': 'Push', 'subtopic': 'Latest draft edit'}}]})
            assert edit.status_code == 200, edit.text
            conflict = commit(third, p3)
            assert conflict.status_code == 409 and conflict.json()['error']['code'] == 'stale_preview', conflict.text
            assert conflict.json()['error']['revision_mismatch'] == 'draft_revision'
            print('TRACE commit HTTP 409:', conflict.json(), 'published:', p3['base_revision'], 'preview draft:', p3['base_draft_revision'], 'latest draft:', edit.json()['draft_revision'])
            recovered = preview(third)
            assert recovered['counts']['created'] == recovered['counts']['removed'] == 1
            review = client.post(imports + '/' + third + '/review', json={'preview_revision': recovered['preview_revision'], 'changes': [{
                'sheet': 'Curriculum', 'row_number': 2, 'action': 'upsert', 'values': ['Grade 1', 'Science', 'Motion', '', 'Push', 'Reviewed correction']}]})
            assert review.status_code == 200, review.text
            t = tree(); renamed = client.patch('/api/v1/admin/curriculum/curriculum/' + cid,
                json={'expected_version': t['version'], 'name': 'Other tab name'})
            assert renamed.status_code == 200, renamed.text
            after_metadata = tree()
            assert after_metadata['published_revision'] == 1
            assert after_metadata['revision'] == 2
            assert after_metadata['base_revision'] == 2  # Only metadata changed, so hierarchy can safely rebase.
            assert commit(third, review.json()).status_code == 409
            final = preview(third)
            rows = client.get(imports + '/' + third + '/review-rows').json()['items']
            assert rows[0]['values'][5] == 'Reviewed correction'
            before = client.get('/api/v1/curricula/' + cid + '/tree').json()
            assert commit(third, final).status_code == 200
            assert client.get('/api/v1/curricula/' + cid + '/tree').json() == before
            publish()
            assert tree()['levels'][0]['subjects'][0]['domains'][0]['topics'][0]['subtopics'][0]['name'] == 'Reviewed correction'
            cancelled = upload(exported.content)
            assert client.post(imports + '/' + cancelled + '/cancel').status_code == 200
            assert client.post(imports + '/' + cancelled + '/preview', json={'sheet_levels': {'Curriculum': '__ALL_LEVELS__'}}).status_code == 422
        finally:
            app.state.database.sessions = original
            outer.rollback()
