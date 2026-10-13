"""Rollback-only curriculum workspace transactions, identities and review operations."""
import os
from contextlib import contextmanager
from io import BytesIO
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy.orm import sessionmaker
from app.core.config import Settings
from app.main import create_app
from app.modules.identity.dependencies import require_admin, require_member
from app.modules.identity.models import AdminRole, StudentProfile
from app.modules.curriculum.import_service import CurriculumImportService
from app.modules.curriculum.workbook_parser import WorkbookRejected

pytestmark = pytest.mark.db_integration

@contextmanager
def isolated_client():
    if os.getenv('FLAME_RUN_DB_TESTS') != '1': pytest.skip('Enable rollback-only integration tests')
    app = create_app(Settings(_env_file=None, environment='test', database_url=Settings().database_url))
    admin = uuid4(); principal = {'id': str(admin), 'role': 'admin'}
    app.dependency_overrides[require_admin] = lambda: principal
    app.dependency_overrides[require_member] = lambda: principal
    with TestClient(app) as client, app.state.database.engine.connect() as connection:
        outer = connection.begin(); original = app.state.database.sessions
        app.state.database.sessions = sessionmaker(bind=connection, expire_on_commit=False, join_transaction_mode='create_savepoint')
        try:
            with app.state.database.session() as session, session.begin():
                session.add_all([StudentProfile(id=admin,auth_subject=str(admin)),AdminRole(auth_subject=str(admin))])
            yield client
        finally:
            app.state.database.sessions = original
            outer.rollback()

def test_workspace_review_atomicity_ids_and_history(monkeypatch):
    with isolated_client() as client:
        code = 'workspace-' + uuid4().hex[:10]
        c = client.post('/api/v1/admin/curricula', json={'code': code,'name':'Workspace fixture'}).json()
        cid = c['id']; root='/api/v1/admin/curricula/'+cid; imports='/api/v1/admin/curriculum/imports'
        def tree(): return client.get(root+'/tree').json()
        def preview(i):
            r=client.post(imports+'/'+i+'/preview',json={'sheet_levels':{'Curriculum':'__ALL_LEVELS__'}})
            assert r.status_code==200,r.text
            return r.json()
        def review(i,p,changes):
            return client.post(imports+'/'+i+'/review',json={'preview_revision':p['preview_revision'],'changes':changes})
        def commit(i,p,confirm=None):
            return client.post(imports+'/'+i+'/commit',headers={'idempotency-key':uuid4().hex},json={'preview_revision':p['preview_revision'],'confirm':confirm or 'REPLACE '+code})
        def upload(payload):
            r=client.post(imports,params={'curriculum_id':cid},files={'file':('workspace.xlsx',payload)})
            assert r.status_code==201,r.text
            return r.json()['import_id']
        def flat(t):
            return [(l,s,d,tp,st) for l in t['levels'] for s in l['subjects'] for d in s['domains']
                    for tp in d.get('topics',[]) for st in tp['subtopics']]
        tree()
        wb=Workbook();sh=wb.active;sh.title='Curriculum'
        sh.append(['Curriculum Code','Level','Subject','Domain','Category','Topic','Subtopic','Learning Outcome','Source URL'])
        for name in ['A basics','B basics']:
            sh.append([code,'Grade 1','Science','Motion',None,'Push',name])
        out=BytesIO();wb.save(out)
        first=upload(out.getvalue());p=preview(first)
        before=tree()
        failed=commit(first,p,'REPLACE wrong')
        assert failed.status_code==422 and tree()==before
        assert commit(first,p).status_code==200
        original=tree(); paths=flat(original)
        t=original
        # Move only one shared-parent path; its sibling retains its IDs and names.
        edit=client.post(root+'/paths/batch',json={'expected_revision':t['draft_revision'],'changes':[{
            'key':'move-one','action':'upsert','source_subtopic_id':paths[0][-1]['id'],
            'values':{'level':'Grade 2','subject':'Science','domain':'Motion','category':'','topic':'Push','subtopic':'A basics'}}]})
        assert edit.status_code==200,edit.text
        moved=tree(); assert len(moved['levels'])==2
        sibling=next(pth for pth in flat(moved) if pth[-1]['name']=='B basics')
        assert sibling[0]['id']==paths[1][0]['id'] and sibling[0]['name']=='Grade 1'
        stale=client.post(root+'/draft/rename',json={'expected_revision':t['draft_revision'],'field':'subject','node_id':sibling[1]['id'],'name':'Natural Science'})
        assert stale.status_code==409
        renamed=client.post(root+'/draft/rename',json={'expected_revision':moved['draft_revision'],'field':'subject','node_id':sibling[1]['id'],'name':'Natural Science'})
        assert renamed.status_code==200,renamed.text
        current=tree()
        exported=client.get(root+'/export',params={'source':'draft'}).content
        second=upload(exported);p=preview(second)
        assert p['counts']['created']==p['counts']['removed']==0
        assert commit(second,p).status_code==200
        assert [(x[0]['id'],x[1]['id'],x[-1]['id']) for x in flat(tree())]==[(x[0]['id'],x[1]['id'],x[-1]['id']) for x in flat(current)]
        third=upload(exported);p=preview(third)
        route=imports+'/'+third
        before_detail=client.get(route).json()
        # A revalidation failure must roll back corrected workbook bytes and token.
        saved_preview=CurriculumImportService._preview
        def reject(*args,**kwargs): raise WorkbookRejected('invalid_workbook')
        monkeypatch.setattr(CurriculumImportService,'_preview',reject)
        response=review(third,p,[{'sheet':'Curriculum','row_number':2,'action':'upsert','values':['Grade 1','Science','Motion','','Push','Must roll back']}])
        assert response.status_code==422,response.text
        after=client.get(route).json()
        assert after['file_hash']==before_detail['file_hash'] and after['preview']['preview_revision']==p['preview_revision']
        monkeypatch.setattr(CurriculumImportService,'_preview',saved_preview)
        inserted=review(third,p,[{'sheet':'Curriculum','action':'add','insert_before':2,'values':['Grade 0','Science','Motion','','Push','Inserted above']}])
        assert inserted.status_code==200,inserted.text
        assert inserted.json()['row_remap']['Curriculum:2']==3
        rows=client.get(route+'/review-rows').json()['items']
        assert rows[0]['values'][5]=='Inserted above'
        deleted=review(third,inserted.json(),[{'sheet':'Curriculum','action':'delete','row_number':3}])
        assert deleted.status_code==200,deleted.text
        assert deleted.json()['row_remap']['Curriculum:4']==3
        missing=client.get(route+'/review-rows',params={'operation':'removed'}).json()
        assert missing['total']==1 and missing['items'][0]['operation']=='removed'
        searched=client.get(route+'/review-rows',params={'q':'Inserted'}).json()
        assert searched['total']==1
        hist=client.get(imports,params={'curriculum_id':cid}).json()['items']
        record=next(item for item in hist if item['import_id']==third)
        assert record['filename']=='workspace.xlsx'
        assert {'uploaded','validated','corrections_failed','corrections_validated'}.issubset({e['status'] for e in record['events']})
        assert commit(third,deleted.json()).status_code==200
        t=tree(); pub=client.post('/api/v1/admin/curriculum/curriculum/'+cid+'/publish',json={'expected_version':t['version'],'expected_draft_revision':t['draft_revision']})
        assert pub.status_code==200,pub.text
        assert client.get('/api/v1/curricula/'+cid+'/tree').status_code==200
        history=client.get(route).json()
        assert history['status']=='committed' and history['events'][-1]['status']=='replacement_draft_created'


def test_replacement_publication_restores_archived_path_and_learning_links():
    from uuid import UUID
    from app.modules.curriculum.models import Subtopic, Topic
    from app.modules.curriculum.path_batch import apply_path_batch
    from app.modules.curriculum.models import Curriculum
    from app.modules.learning.models import LearningMembership
    from fastapi import HTTPException

    with isolated_client() as client:
        code = 'restore-' + uuid4().hex[:10]
        c = client.post('/api/v1/admin/curricula', json={'code': code, 'name': 'Restore fixture'}).json()
        cid = c['id']; root = '/api/v1/admin/curricula/' + cid
        imports = '/api/v1/admin/curriculum/imports'
        publish_url = '/api/v1/admin/curriculum/curriculum/' + cid + '/publish'

        def tree(): return client.get(root + '/tree').json()
        def publish(t):
            return client.post(publish_url, json={'expected_version': t['version'], 'expected_draft_revision': t['draft_revision']})
        def replace(payload):
            uploaded = client.post(imports, params={'curriculum_id': cid}, files={'file': ('restore.xlsx', payload)})
            assert uploaded.status_code == 201, uploaded.text
            route = imports + '/' + uploaded.json()['import_id']
            preview = client.post(route + '/preview', json={'sheet_levels': {'Curriculum': '__ALL_LEVELS__'}})
            assert preview.status_code == 200, preview.text
            result = client.post(route + '/commit', headers={'idempotency-key': uuid4().hex}, json={
                'preview_revision': preview.json()['preview_revision'], 'confirm': 'REPLACE ' + code})
            assert result.status_code == 200, result.text
        def workbook(include_retired):
            wb = Workbook(); sh = wb.active; sh.title = 'Curriculum'
            sh.append(['Curriculum Code', 'Level', 'Subject', 'Domain', 'Category', 'Topic', 'Subtopic', 'Learning Outcome', 'Source URL'])
            sh.append([code, 'Grade 1', 'Science', 'Motion', '', 'Keep', 'Keep lesson'])
            if include_retired:
                sh.append([code, 'Grade 1', 'Science', 'Motion', '', 'Retired', 'Restored lesson'])
            out = BytesIO(); wb.save(out); return out.getvalue()

        tree(); replace(workbook(True)); first = publish(tree())
        assert first.status_code == 200, first.text
        exported = client.get(root + '/export', params={'source': 'published'}).content
        t = tree(); level = t['levels'][0]; subject = level['subjects'][0]; domain = subject['domains'][0]
        topic = next(item for item in domain['topics'] if item['name'] == 'Retired')
        leaf = topic['subtopics'][0]; leaf_id = UUID(leaf['id']); topic_id = UUID(topic['id'])
        student_id = UUID(client.app.dependency_overrides[require_admin]()['id'])
        membership_id = uuid4()
        with client.app.state.database.session() as session, session.begin():
            session.add(LearningMembership(id=membership_id, student_id=student_id, curriculum_id=UUID(cid),
                level_id=UUID(level['id']), subject_id=UUID(subject['id']), domain_id=UUID(domain['id']),
                topic_id=topic_id, subtopic_id=leaf_id))

        replace(workbook(False)); removed = publish(tree())
        assert removed.status_code == 200, removed.text
        with client.app.state.database.session() as session:
            assert session.get(Subtopic, leaf_id).archived
            assert session.get(Topic, topic_id).archived
            assert session.get(LearningMembership, membership_id).subtopic_id == leaf_id
            # Restoration is limited to explicit publication, not general row writes.
            with pytest.raises(HTTPException) as conflict:
                apply_path_batch(session, session.get(Curriculum, UUID(cid)), [{
                    'key': 'unreviewed-restore', 'action': 'upsert', 'values': {
                        'level': 'Grade 1', 'subject': 'Science', 'domain': 'Motion', 'category': '',
                        'topic': 'Retired', 'subtopic': 'Restored lesson'}}])
            assert conflict.value.detail['code'] == 'archived_path_conflict'
            session.rollback()

        replace(exported); current = tree()
        assert client.get('/api/v1/curricula/' + cid + '/tree').json()['levels'][0]['subjects'][0]['domains'][0]['topics'][0]['name'] == 'Keep'
        # The same genuine stale-version checks still reject publication.
        assert publish({**current, 'version': current['version'] - 1}).status_code == 409
        assert publish({**current, 'draft_revision': current['draft_revision'] - 1}).status_code == 409
        restored = publish(current)
        assert restored.status_code == 200, restored.text
        assert restored.json()['revision'] == removed.json()['revision'] + 1
        with client.app.state.database.session() as session:
            assert not session.get(Subtopic, leaf_id).archived
            assert not session.get(Topic, topic_id).archived
            assert session.get(LearningMembership, membership_id).subtopic_id == leaf_id
        member = client.get('/api/v1/curricula/' + cid + '/tree').json()
        restored_topic = next(item for item in member['levels'][0]['subjects'][0]['domains'][0]['topics'] if item['name'] == 'Retired')
        assert restored_topic['id'] == str(topic_id)
        assert restored_topic['subtopics'][0]['id'] == str(leaf_id)
