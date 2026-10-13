"""Provider parsing/verification and strict playback policy; no real videos mutated."""
from uuid import uuid4, UUID
import pytest
import httpx
from fastapi import HTTPException
from pydantic import SecretStr
from sqlalchemy import select
from app.core.config import Settings
from app.modules.resources import external_video as adapters
from app.modules.resources.models import Resource
from test_curriculum_workspace import isolated_client

@pytest.mark.parametrize('url,provider,identity',[
    ('https://www.youtube.com/watch?v=M7lc1UVf-VE&si=tracking','youtube','M7lc1UVf-VE'),
    ('https://youtu.be/M7lc1UVf-VE?t=15','youtube','M7lc1UVf-VE'),
    ('https://m.youtube.com/shorts/M7lc1UVf-VE','youtube','M7lc1UVf-VE'),
    ('https://www.youtube-nocookie.com/embed/M7lc1UVf-VE','youtube','M7lc1UVf-VE'),
    ('https://youtube.com/live/M7lc1UVf-VE','youtube','M7lc1UVf-VE'),
    ('https://vimeo.com/76979871','vimeo','76979871'),
    ('https://player.vimeo.com/video/76979871?autoplay=1','vimeo','76979871'),
    ('https://vimeo.com/channels/staffpicks/76979871','vimeo','76979871'),
])
def test_supported_url_formats(url,provider,identity):
    parsed=adapters.parse_video(url);assert parsed['provider']==provider and parsed['video_id']==identity
    assert 'si=' not in parsed['canonical_url'] and 'autoplay=' not in parsed['canonical_url']

@pytest.mark.parametrize('url',[
    'http://youtube.com/watch?v=M7lc1UVf-VE','https://youtube.com.evil.test/watch?v=M7lc1UVf-VE',
    'https://youtube.com@127.0.0.1/watch?v=M7lc1UVf-VE','https://youtube.com:444/watch?v=M7lc1UVf-VE',
    'https://youtube.com/playlist?list=abc','https://youtube.com/watch?v=M7lc1UVf-VE&v=abcdefghijk',
    'https://youtube.com/embed/%3Cscript%3E','https://youtube.com/watch?v=bad','https://youtube.com/watch?v=M7lc1UVf-VE#unsafe',
    'https://vimeo.com/76979871/privatehash','https://player.vimeo.com/video/76979871?h=private',
    'https://localhost/video/76979871','https://other-provider.test/video/1','<iframe src="https://youtube.com/embed/M7lc1UVf-VE"></iframe>',
])
def test_reject_unsafe_unsupported_and_private_formats(url):
    with pytest.raises(HTTPException) as failure:adapters.parse_video(url)
    assert failure.value.status_code==422

def fixture_provider(endpoint,*,params=None,headers=None):
    if 'oembed' in endpoint:
        vimeo='vimeo' in endpoint
        return {'type':'video','title':'Gravity lesson','author_name':'Licensed author','description':'Falling objects',
                'video_id':76979871,'thumbnail_url':'https://i.vimeocdn.com/video/123.jpg' if vimeo else 'https://i.ytimg.com/vi/M7lc1UVf-VE/hqdefault.jpg','html':'<script>NEVER RENDER</script>'}
    if 'googleapis' in endpoint:
        assert 'key' not in params and headers['X-Goog-Api-Key']=='fixture-key'
        return {'items':[{'id':params['id'],'status':{'privacyStatus':'public','uploadStatus':'processed','embeddable':True}}]}
    assert headers['Authorization']=='Bearer fixture-token'
    return {'uri':'/videos/76979871','status':'available','privacy':{'view':'anybody','embed':'public'}}

def test_keyless_metadata_allows_standard_playback(monkeypatch):
    def keyless(endpoint,**kwargs):
        assert 'oembed' in endpoint, 'No credentialed provider API should be called'
        return fixture_provider(endpoint,**kwargs)
    monkeypatch.setattr(adapters,'provider_json',keyless)
    config=Settings(_env_file=None,resource_youtube_api_key='unused',resource_vimeo_api_token='unused')
    for url in ['https://youtu.be/M7lc1UVf-VE','https://vimeo.com/76979871']:
        data=adapters.inspect_video(url,config)
        assert data['verification']=='metadata_only' and data['embeddable'] is None and data['student_playback_allowed'] and 'html' not in data
    assert adapters.thumbnail_url('https://evil.test/thumbnail','youtube') is None

def test_provider_failure_and_truncated_private_metadata(monkeypatch):
    monkeypatch.setattr(adapters,'provider_json',lambda *a,**k:{'type':'video','video_id':76979871})
    with pytest.raises(HTTPException) as error:adapters.inspect_video('https://vimeo.com/76979871',Settings(_env_file=None))
    assert error.value.detail['code']=='external_video_unavailable'
    def offline(*a,**k):adapters.reject('external_video_verification_failed',503)
    monkeypatch.setattr(adapters,'provider_json',offline)
    with pytest.raises(HTTPException) as error:adapters.inspect_video('https://vimeo.com/76979871',Settings(_env_file=None))
    assert error.value.status_code==503

@pytest.mark.parametrize('status,payload,expected',[
    (403,b'private',422),(404,b'missing',422),(302,b'redirect',503),
    (429,b'rate limit',503),(200,b'not json',503),(200,b'x'*262145,503),
],ids=['forbidden','missing','redirect','rate-limit','invalid-json','oversize'])
def test_provider_transport_is_bounded_and_does_not_redirect(monkeypatch,status,payload,expected):
    original=httpx.Client;requests=[]
    def answer(request):
        requests.append(str(request.url));return httpx.Response(status,content=payload,headers={'location':'https://evil.test/redirect'})
    def client(**kwargs):
        assert kwargs['follow_redirects'] is False and kwargs['trust_env'] is False
        return original(**kwargs,transport=httpx.MockTransport(answer))
    monkeypatch.setattr(adapters.httpx,'Client',client)
    with pytest.raises(HTTPException) as error:adapters.provider_json('https://www.youtube.com/oembed',params={'url':'https://www.youtube.com/watch?v=M7lc1UVf-VE'})
    assert error.value.status_code==expected and len(requests)==1

def test_external_video_keyless_publication_and_embed_delivery(monkeypatch):
    monkeypatch.setattr(adapters,'provider_json',fixture_provider)
    with isolated_client() as client:
        config=client.app.state.settings
        inspect=client.post('/api/v1/admin/resources/external-video/inspect',json={'url':'https://youtu.be/M7lc1UVf-VE'})
        assert inspect.status_code==200 and inspect.json()['verification']=='metadata_only'
        row=client.post('/api/v1/admin/resources',json={'type':'external_video','title':'External fixture','external_url':'https://youtu.be/M7lc1UVf-VE',
            'caption_or_transcript':'Gravity pulls objects toward Earth.','rights_basis':'licensed','rights_reference':'fixture permission','rights_holder':'Fixture','distribution_scope':'members'}).json()
        root='/api/v1/admin/resources/'+row['id'];assert row['paths']==[] and row['external_video']['provider']=='youtube'
        response=client.post(root+'/publish',json={'expected_version':row['version']});assert response.status_code==200;row=response.json()
        assert client.get(root).json()['version']==row['version']
        assert config.resource_youtube_api_key is None and config.resource_vimeo_api_token is None
        response=client.patch(root,json={'expected_version':row['version'],'external_url':'https://vimeo.com/76979871','title':'Vimeo fixture'});assert response.status_code==200;row=response.json();assert row['external_video']['provider']=='vimeo'
        assert client.patch(root,json={'expected_version':1,'title':'stale'}).status_code==409
        response=client.post(root+'/publish',json={'expected_version':row['version']});assert response.status_code==200;row=response.json()
        c=client.post('/api/v1/admin/curricula',json={'code':'external-'+uuid4().hex[:8],'name':'External fixture'}).json();cid=c['id']
        def child(kind,parent,name):return client.post('/api/v1/admin/curriculum/'+kind,json={'parent_id':parent,'name':name}).json()['id']
        level=child('level',cid,'Grade 1');subject=child('subject',level,'Science');domain=child('domain',subject,'Motion');topic=child('topic',domain,'Gravity');leaf=child('subtopic',topic,'Fall')
        tree=client.get('/api/v1/admin/curricula/'+cid+'/tree').json();assert client.post('/api/v1/admin/curriculum/curriculum/'+cid+'/publish',json={'expected_version':tree['version'],'expected_draft_revision':tree['draft_revision']}).status_code==200
        for paths in [[{'topic_id':topic,'subtopic_id':None},{'topic_id':topic,'subtopic_id':leaf}],[],[{'topic_id':topic,'subtopic_id':leaf}]]:
            response=client.patch(root,json={'expected_version':row['version'],'paths':paths});assert response.status_code==200;row=response.json();assert row['published'] and row['paths']==paths
        preview=client.get(root+'/preview').json();assert preview['launch_mode']=='external_video' and preview['url'].startswith('https://player.vimeo.com/video/76979871') and 'html' not in preview
        assert client.get('/api/v1/resources',params={'topic_id':topic,'subtopic_id':leaf}).json()['items'][0]['id']==row['id']
        blocked=client.get('/api/v1/resources/'+row['id']+'/delivery');assert blocked.status_code==200 and blocked.json()['launch_mode']=='external_video'
        # An old stored strict-mode block cannot override the current server playback policy.
        with client.app.state.database.session() as db,db.begin():
            stored=db.get(Resource,UUID(row['id']));stored.external_video={**stored.external_video,'student_playback_allowed':False}
        assert client.get(root).json()['external_video']['student_playback_allowed']
        assert client.post('/api/v1/admin/resources',json={'type':'interactive','title':'Bypass','external_url':'https://vimeo.com/76979871'}).status_code==422
        response=client.post(root+'/unpublish',json={'expected_version':row['version']});assert response.status_code==200;row=response.json();assert not row['published']
        assert client.post(root+'/delete',json={'expected_version':row['version'],'confirm_resource_id':row['id']}).status_code==200
        assert client.get(root).status_code==404

