from io import BytesIO
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from uuid import uuid4
import pytest
from PIL import Image
from pydantic import SecretStr
from app.modules.resources.external_video import video_data
from test_curriculum_workspace import isolated_client


def test_youtube_thumbnail_is_safe_without_old_metadata():
    row = SimpleNamespace(type="video", external_url="https://youtu.be/abcdefghijk", external_video=None)
    assert video_data(row)["thumbnail_url"] == "https://i.ytimg.com/vi/abcdefghijk/hqdefault.jpg"
    row.external_video = {"thumbnail_url": "https://evil.test/tracker.jpg"}
    assert video_data(row)["thumbnail_url"].startswith("https://i.ytimg.com/")


@pytest.mark.db_integration
def test_video_thumbnail_ownership_publication_delivery_and_withdrawal():
    with TemporaryDirectory() as directory, isolated_client() as client:
        config=client.app.state.settings;config.resource_local_dir=directory;config.bff_shared_key=SecretStr('thumbnail-fixture')
        c=client.post('/api/v1/admin/curricula',json={'code':'thumb-'+uuid4().hex[:10],'name':'Thumbnail test'}).json()
        def child(kind,parent,name):
            response=client.post('/api/v1/admin/curriculum/'+kind,json={'parent_id':parent,'name':name});assert response.status_code==201,response.text
            return response.json()['id']
        level=child('level',c['id'],'Grade 1');subject=child('subject',level,'Science');domain=child('domain',subject,'Motion');topic=child('topic',domain,'Gravity');child('subtopic',topic,'Falling')
        tree=client.get('/api/v1/admin/curricula/'+c['id']+'/tree').json()
        published=client.post('/api/v1/admin/curriculum/curriculum/'+c['id']+'/publish',json={'expected_version':tree['version'],'expected_draft_revision':tree['draft_revision']});assert published.status_code==200,published.text
        image=BytesIO();Image.new('RGB',(160,90),'green').save(image,'PNG');png=image.getvalue()
        def upload(name,body,mime):
            result=client.post('/api/v1/admin/resources/uploads',files={'file':(name,body,mime)});assert result.status_code==201,result.text
            return result.json()['upload_id']
        video=upload('film.mp4',b'\x00\x00\x00\x18ftypmp42'+b'\x00'*24,'video/mp4')
        poster=upload('poster.png',png,'image/png')
        body={'type':'video','title':'Gravity video','upload_id':video,'paths':[{'topic_id':topic}], 'rights_basis':'owned','rights_holder':'Fixture','distribution_scope':'members','accessibility_note':'Captions included'}
        saved=client.post('/api/v1/admin/resources',json=body);assert saved.status_code==201,saved.text
        row=saved.json();root='/api/v1/admin/resources/'+row['id'];member='/api/v1/resources/'+row['id']
        missing=client.post(root+'/publish',json={'expected_version':row['version']});assert missing.status_code==422
        assert missing.json()['error']['code']=='video_thumbnail_required'
        invalid=client.patch(root,json={'expected_version':row['version'],'thumbnail_upload_id':video});assert invalid.status_code==422
        saved=client.patch(root,json={'expected_version':row['version'],'thumbnail_upload_id':poster});assert saved.status_code==200,saved.text
        row=saved.json();assert row['has_thumbnail'] and row['thumbnail_upload_id']==poster
        assert client.get(root+'/preview?thumbnail=true').status_code==200
        assert client.get(root+'/preview-content?thumbnail=true').content==png
        reused=client.post('/api/v1/admin/resources',json={**body,'upload_id':upload('other.mp4',b'\x00\x00\x00\x18ftypmp42'+b'\x00'*24,'video/mp4'),'thumbnail_upload_id':poster});assert reused.status_code==409
        response=client.post(root+'/publish',json={'expected_version':row['version']});assert response.status_code==200,response.text
        row=response.json();query={'topic_id':topic,'curriculum_revision':published.json()['revision'],'version':row['version'],'thumbnail':True}
        delivered=client.get(member+'/delivery',params=query);assert delivered.status_code==200,delivered.text
        assert 'storage_key' not in delivered.text
        url=delivered.json()['url'];assert client.get(url).content==png
        assert client.get(url.replace('thumbnail=true','thumbnail=false')).status_code==404
        assert client.get(member+'/delivery',params={**query,'version':1}).status_code==409
        assert client.get(member+'/delivery').json()['poster_url']
        assert client.post(root+'/unpublish',json={'expected_version':row['version']}).status_code==200
        assert client.get(url).status_code==404
        unpublished=client.get(root).json()
        cleared=client.patch(root,json={'expected_version':unpublished['version'],'thumbnail_upload_id':None});assert cleared.status_code==200,cleared.text
        assert not cleared.json()['has_thumbnail']
        assert client.post(root+'/publish',json={'expected_version':cleared.json()['version']}).status_code==422
