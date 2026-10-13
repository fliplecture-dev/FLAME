"""Rollback-only library filtering and original GIF lifecycle coverage."""
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from uuid import UUID, uuid4
import pytest
from PIL import Image
from pydantic import SecretStr
from app.modules.resources.models import Resource
from app.modules.resources.validation import declared_format, inspect_media, MediaRejected
from app.modules.conversations.models import ConversationSession, Message
from app.modules.identity.dependencies import require_admin
from test_curriculum_workspace import isolated_client


def gif_bytes():
    out = BytesIO()
    Image.new('RGB', (60, 30), 'red').save(out, 'GIF', save_all=True,
        append_images=[Image.new('RGB', (60, 30), 'blue')], duration=100, loop=0)
    return out.getvalue()


def test_gif_validation_rejects_disguised_and_corrupt_media(tmp_path):
    assert declared_format('force.gif', 'image/gif')[2] == 'animation'
    with pytest.raises(MediaRejected): declared_format('force.gif', 'image/png')
    good = tmp_path/'good.gif'; good.write_bytes(gif_bytes()); inspect_media(good,'image/gif')
    bad = tmp_path/'bad.gif'; bad.write_bytes(b'GIF89a' + b'broken')
    with pytest.raises(MediaRejected): inspect_media(bad,'image/gif')
    bad.write_bytes(gif_bytes()[:-25])
    with pytest.raises(MediaRejected): inspect_media(bad,'image/gif')


def test_server_filters_and_gif_draft_publish_delivery_lifecycle():
    with TemporaryDirectory() as directory, isolated_client() as client:
        client.app.state.settings.resource_local_dir=directory
        client.app.state.settings.resource_storage_backend='local'
        client.app.state.settings.bff_shared_key=SecretStr('gif-fixture-secret')
        client.app.state.settings.resource_allowed_hosts='media.example.test'
        code='library-'+uuid4().hex[:8]
        c=client.post('/api/v1/admin/curricula',json={'code':code,'name':'Library fixture'}).json();cid=c['id']
        def child(kind,parent,name,**extra):
            response=client.post('/api/v1/admin/curriculum/'+kind,json={'parent_id':parent,'name':name,**extra})
            assert response.status_code==201,response.text
            return response.json()['id']
        level=child('level',cid,'Grade 1');subject=child('subject',level,'Science');domain=child('domain',subject,'Motion')
        category=child('category',domain,'Movement');topic=child('topic',domain,'Force',category_id=category)
        leaf1=child('subtopic',topic,'Push');leaf2=child('subtopic',topic,'Pull')
        other=child('topic',domain,'Gravity');leaf3=child('subtopic',other,'Falling')
        tree=client.get('/api/v1/admin/curricula/'+cid+'/tree').json()
        pub=client.post('/api/v1/admin/curriculum/curriculum/'+cid+'/publish',json={'expected_version':tree['version'],'expected_draft_revision':tree['draft_revision']})
        assert pub.status_code==200,pub.text
        revision=pub.json()['revision']
        payload=gif_bytes()
        def upload():
            response=client.post('/api/v1/admin/resources/uploads',files={'file':('force-motion.gif',payload,'image/gif')})
            assert response.status_code==201,response.text
            assert response.json()['mime_type']=='image/gif' and response.json()['media_type']=='animation'
            return response.json()['upload_id']
        assert client.post('/api/v1/admin/resources/uploads',files={'file':('bad.gif',b'GIF89a broken','image/gif')}).status_code==422
        assert client.post('/api/v1/admin/resources/uploads',files={'file':('bad.gif',payload,'image/png')}).status_code==422
        assert client.post('/api/v1/admin/resources/uploads',files={'file':('large.gif',b'GIF89a'+b'0'*(10*1024*1024),'image/gif')}).status_code==413
        identity=uuid4()
        saved=client.post('/api/v1/admin/resources',json={'creation_id':str(identity),'type':'animation','title':code+' Force animation','upload_id':upload(),
            'paths':[{'topic_id':topic},{'topic_id':topic,'subtopic_id':leaf1}], 'alt_text':'A moving arrow pushes a box.',
            'rights_basis':'owned','rights_holder':'Fixture','distribution_scope':'members'})
        assert saved.status_code==201,saved.text
        row=saved.json();rid=row['id'];assert row['mime_type']=='image/gif' and row['file_name']=='force-motion.gif' and row['updated_at']
        assert row['published'] is False
        preview=client.get('/api/v1/admin/resources/'+rid+'/preview-content')
        assert preview.status_code==200 and preview.content==payload and preview.headers['content-type']=='image/gif'
        with client.app.state.database.session() as db:
            assert (Path(directory)/db.get(Resource,UUID(rid)).storage_key).read_bytes()==payload
        def external(title,paths):
            response=client.post('/api/v1/admin/resources',json={'type':'image','title':code+' '+title,'external_url':'https://media.example.test/figure.png','paths':paths})
            assert response.status_code==201,response.text
            return response.json()
        direct=external('Direct Pull',[{'topic_id':topic,'subtopic_id':leaf2}]); unrelated=external('Gravity',[{'topic_id':other,'subtopic_id':leaf3}])
        def listing(**filters):
            response=client.get('/api/v1/admin/resources',params={'q':code,**filters});assert response.status_code==200,response.text
            return response.json()
        assert listing(subtopic_id=leaf1)['total']==1
        assert {r['id'] for r in listing(subtopic_id=leaf2)['items']}=={rid,direct['id']}
        assert listing(topic_id=topic)['total']==2  # no duplicate for two mappings
        for field,value in [('curriculum_id',cid),('level_id',level),('subject_id',subject),('domain_id',domain)]: assert listing(**{field:value})['total']==3
        assert listing(category_id=category)['total']==2
        assert listing(format='GIF')['total']==1 and listing(type='animation')['total']==1
        assert listing(format='URL')['total']==2
        assert listing(subtopic_id=leaf3,topic_id=topic)['total']==0
        pages=[listing(sort='title',direction='asc',limit=1,offset=i) for i in range(3)]
        assert all(p['total']==3 for p in pages) and len({p['items'][0]['id'] for p in pages})==3
        original_upload=row['upload_id']
        edited=client.patch('/api/v1/admin/resources/'+rid,json={'expected_version':row['version'],'description':'Metadata-only change'})
        assert edited.status_code==200,edited.text;row=edited.json();assert row['upload_id']==original_upload and not row['published']
        failed=client.patch('/api/v1/admin/resources/'+rid,json={'expected_version':1,'title':'Must not save'})
        assert failed.status_code==409 and client.get('/api/v1/admin/resources/'+rid).json()['title']!= 'Must not save'
        replacement=client.patch('/api/v1/admin/resources/'+rid,json={'expected_version':row['version'],'upload_id':upload()})
        assert replacement.status_code==200,replacement.text;row=replacement.json();assert row['upload_id']!=original_upload
        blocked=client.patch('/api/v1/admin/resources/'+rid,json={'expected_version':row['version'],'alt_text':'gif'})
        row=blocked.json()
        assert client.post('/api/v1/admin/resources/'+rid+'/publish',json={'expected_version':row['version']}).status_code==422
        row=client.patch('/api/v1/admin/resources/'+rid,json={'expected_version':row['version'],'alt_text':'An animated force arrow pushes a box.'}).json()
        published=client.post('/api/v1/admin/resources/'+rid+'/publish',json={'expected_version':row['version']})
        assert published.status_code==200,published.text;row=published.json()
        assert listing(published=True)['total']==1
        lookup=client.get('/api/v1/resources',params={'topic_id':topic,'subtopic_id':leaf2,'curriculum_revision':revision})
        assert [r['id'] for r in lookup.json()['items']]==[rid]
        delivery=client.get('/api/v1/resources/'+rid+'/delivery');assert delivery.status_code==200,delivery.text
        url=urlsplit(delivery.json()['url']);content=client.get(url.path+'?'+url.query)
        assert content.content==payload and content.headers['content-type']=='image/gif'
        admin=client.app.dependency_overrides[require_admin]()['id']
        with client.app.state.database.session() as db,db.begin():
            conversation=ConversationSession(student_id=UUID(admin),mode='study',curriculum_id=UUID(cid),revision=revision,
                context_snapshot={'curriculum_id':cid,'level_id':level,'subject_id':subject,'domain_id':domain,'category_id':category,'topic_id':topic,'subtopic_id':leaf2})
            db.add(conversation);db.flush()
            db.add(Message(session_id=conversation.id,turn_number=1,role='user',blocks=[{'kind':'text','text':'explain force'}]))
            answer=Message(session_id=conversation.id,turn_number=1,role='assistant',blocks=[{'kind':'text','text':'Force is a push that moves a box.'}],resolved_curriculum_id=UUID(cid),resolved_subject_id=UUID(subject),resolved_topic_id=UUID(topic),resolved_revision=revision)
            db.add(answer);db.flush();sid=str(conversation.id);mid=str(answer.id)
        recommendation=client.get('/api/v1/sessions/'+sid+'/recommendations',params={'message_id':mid})
        assert recommendation.status_code==200,recommendation.text
        assert recommendation.json()['image_decision']['resource_id']==rid and recommendation.json()['image_decision']['display_mode']=='inline'
        assert recommendation.json()['resources'][0]['mime_type']=='image/gif'
        removed=client.post('/api/v1/admin/resources/'+rid+'/unpublish',json={'expected_version':row['version']})
        assert removed.status_code==200,removed.text
        assert removed.json()['paths']==row['paths'] and removed.json()['upload_id']==row['upload_id']
        assert client.get('/api/v1/resources/'+rid+'/delivery').status_code==404
