"""Media-only creation, live mapping updates and retained resource deletion."""
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4
from pathlib import Path
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select
from app.modules.resources.models import Resource, ResourceTopic, ResourceUpload
from app.modules.activity_kits.models import ActivityKit
from app.modules.conversations.models import ConversationSession, Message
from app.modules.identity.dependencies import require_admin
from test_curriculum_workspace import isolated_client
from test_resource_library import gif_bytes


def test_unmapped_publication_live_mapping_and_retained_deletion():
    with TemporaryDirectory() as directory, isolated_client() as client:
        settings=client.app.state.settings;settings.resource_local_dir=directory;settings.bff_shared_key=SecretStr('mapping-fixture-secret');settings.resource_allowed_hosts='media.example.test'
        created=client.post('/api/v1/admin/curricula',json={'code':'mapping-'+uuid4().hex[:10],'name':'Mapping fixture'}).json();cid=created['id']
        def child(kind,parent,name):
            r=client.post('/api/v1/admin/curriculum/'+kind,json={'parent_id':parent,'name':name});assert r.status_code==201,r.text
            return r.json()['id']
        level=child('level',cid,'Grade 1');subject=child('subject',level,'Science');domain=child('domain',subject,'Motion')
        topic=child('topic',domain,'Force');leaf1=child('subtopic',topic,'Push');leaf2=child('subtopic',topic,'Pull')
        other=child('topic',domain,'Gravity');otherleaf=child('subtopic',other,'Fall')
        tree=client.get('/api/v1/admin/curricula/'+cid+'/tree').json()
        pub=client.post('/api/v1/admin/curriculum/curriculum/'+cid+'/publish',json={'expected_version':tree['version'],'expected_draft_revision':tree['draft_revision']});assert pub.status_code==200,pub.text
        revision=pub.json()['revision']
        upload=client.post('/api/v1/admin/resources/uploads',files={'file':('force.gif',gif_bytes(),'image/gif')});assert upload.status_code==201,upload.text
        response=client.post('/api/v1/admin/resources',json={'type':'animation','title':'Force animation','upload_id':upload.json()['upload_id'],
            'alt_text':'A moving force arrow pushes a box','rights_basis':'owned','rights_holder':'Fixture','distribution_scope':'members'})
        assert response.status_code==201,response.text
        row=response.json();rid=row['id'];assert row['paths']==[] and not row['published']
        response=client.post('/api/v1/admin/resources/'+rid+'/publish',json={'expected_version':row['version']});assert response.status_code==200,response.text
        row=response.json();assert row['published'] and row['paths']==[]
        assert client.get('/api/v1/resources/'+rid+'/delivery').status_code==404
        def update(paths,version=None):
            return client.patch('/api/v1/admin/resources/'+rid,json={'expected_version':version or row['version'],'paths':paths})
        def visible(topic_id,leaf):
            r=client.get('/api/v1/resources',params={'topic_id':topic_id,'subtopic_id':leaf});assert r.status_code==200,r.text
            return [item['id'] for item in r.json()['items']]
        paths=[{'topic_id':topic,'subtopic_id':None},{'topic_id':other,'subtopic_id':otherleaf}]
        response=update(paths);assert response.status_code==200,response.text;row=response.json()
        assert row['published'] and len(row['paths'])==2
        assert rid in visible(topic,leaf1) and rid in visible(topic,leaf2) and rid in visible(other,otherleaf)
        before=row['version'];response=update([{'topic_id':topic,'subtopic_id':otherleaf}]);assert response.status_code==422
        assert client.get('/api/v1/admin/resources/'+rid).json()['paths']==row['paths']
        assert update([],version=1).status_code==409
        assert client.get('/api/v1/admin/resources/'+rid).json()['version']==before
        response=update([]);assert response.status_code==200,response.text;row=response.json()
        assert row['published'] and row['paths']==[] and rid not in visible(topic,leaf1)
        assert client.get('/api/v1/resources/'+rid+'/delivery').status_code==404
        response=update(paths);assert response.status_code==200,response.text;row=response.json()
        admin=client.app.dependency_overrides[require_admin]()['id']
        with client.app.state.database.session() as db,db.begin():
            original=db.get(Resource,UUID(rid));storage_key=original.storage_key
            shared=Resource(type='animation',title='Shared retained animation',storage_key=storage_key,mime_type='image/gif',byte_size=original.byte_size,
                alt_text='A moving box',rights_basis='owned',rights_holder='Fixture',distribution_scope='members',published=True)
            db.add(shared);db.flush();shared_id=str(shared.id)
            db.add(ResourceTopic(resource_id=shared.id,topic_id=UUID(topic)))
            kit=ActivityKit(name='Media dependency',image_keys=[storage_key]);db.add(kit);db.flush();kit_id=kit.id
            conversation=ConversationSession(student_id=UUID(admin),mode='study',curriculum_id=UUID(cid),revision=revision,
                context_snapshot={'curriculum_id':cid,'level_id':level,'subject_id':subject,'domain_id':domain,'topic_id':topic,'subtopic_id':leaf1})
            db.add(conversation);db.flush();sid=str(conversation.id)
            db.add(Message(session_id=conversation.id,turn_number=1,role='user',blocks=[{'kind':'text','text':'explain force'}]))
            answer=Message(session_id=conversation.id,turn_number=1,role='assistant',blocks=[{'kind':'text','text':'Force pushes a box.'}],resolved_curriculum_id=UUID(cid),resolved_subject_id=UUID(subject),resolved_topic_id=UUID(topic),resolved_revision=revision)
            db.add(answer);db.flush();mid=str(answer.id)
        recommendation=client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':mid});assert recommendation.status_code==200,recommendation.text
        assert recommendation.json()['recommendation_decision']['primary']['candidate_id']==rid
        assert recommendation.json()['recommendation_decision']['primary']['display_mode']=='optional card'
        activity=client.post('/api/v1/resources/'+rid+'/activity',json={'event_type':'open','deduplication_key':uuid4().hex,'session_id':sid});assert activity.status_code==200,activity.text
        impact=client.get('/api/v1/admin/resources/'+rid+'/delete-preview');assert impact.status_code==200,impact.text
        assert impact.json()['dependencies']['shared_resources']==1 and impact.json()['dependencies']['activity_kits']==1
        assert impact.json()['dependencies']['activity_records']==1 and impact.json()['dependencies']['conversation_references']==1
        assert impact.json()['recoverable_in_admin'] is False and impact.json()['media_retained'] is True
        # Read-only/cancelled confirmation does not remove mappings.
        assert client.get('/api/v1/admin/resources/'+rid).json()['paths']==row['paths']
        body={'expected_version':row['version'],'confirm_resource_id':rid}
        denied=client.post('/api/v1/admin/resources/'+rid+'/delete',json={**body,'confirm_resource_id':str(uuid4())});assert denied.status_code==422
        assert client.post('/api/v1/admin/resources/'+rid+'/delete',json={**body,'expected_version':1}).status_code==409
        original_override=client.app.dependency_overrides[require_admin]
        def forbidden():raise HTTPException(403,'admin_required')
        client.app.dependency_overrides[require_admin]=forbidden
        assert client.post('/api/v1/admin/resources/'+rid+'/delete',json=body).status_code==403
        client.app.dependency_overrides[require_admin]=original_override
        deleted=client.post('/api/v1/admin/resources/'+rid+'/delete',json=body);assert deleted.status_code==200,deleted.text
        assert client.post('/api/v1/admin/resources/'+rid+'/delete',json=body).status_code==200 # lost-response retry
        assert client.get('/api/v1/admin/resources/'+rid).status_code==404
        assert client.get('/api/v1/admin/resources/'+rid+'/preview-content').status_code==404
        assert client.get('/api/v1/resources/'+rid+'/delivery').status_code==404
        assert rid not in [r['id'] for r in client.get('/api/v1/admin/resources',params={'q':'Force animation'}).json()['items']]
        assert client.get('/api/v1/resources/'+shared_id+'/delivery').status_code==200
        assert client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':mid}).json()['image_decision']['display_mode']=='none'
        with client.app.state.database.session() as db:
            retained=db.get(Resource,UUID(rid));assert retained.deleted_at and retained.deletion_snapshot['resource']['paths']==row['paths']
            assert not db.scalars(select(ResourceTopic).where(ResourceTopic.resource_id==retained.id)).all()
            assert db.scalar(select(ResourceUpload).where(ResourceUpload.resource_id==retained.id))
            assert (Path(directory)/storage_key).read_bytes()==gif_bytes()
            assert db.get(ActivityKit,kit_id).image_keys==[storage_key]
