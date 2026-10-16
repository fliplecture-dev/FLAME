"""Interactive HTML isolation and rollback-only catalogue lifecycle."""
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

import pytest
import httpx
from pydantic import SecretStr
from app.modules.functional.resources.interactive import HTML_LIMIT, InvalidInteractive, isolated_document, validate_document
from app.modules.functional.resources.validation import MEDIA_TYPES, FORMATS, MediaRejected, declared_format, inspect_media
from app.modules.functional.resources.storage import ResourceStorage, StorageUnavailable
from app.core.config import Settings
from app.modules.application.recommendations.selection import learning_need, select_recommendations
from app.modules.application.recommendations.evaluation import evaluate
from test_curriculum_workspace import isolated_client

HTML = b'<!doctype html><html><head><title>Gravity</title><style>body{color:green}</style></head><body><button id="go">Drop</button><script>document.getElementById("go").onclick=()=>{document.body.dataset.dropped="yes"}</script></body></html>'


def test_html_formats_isolation_and_existing_families(tmp_path):
    assert declared_format('lab.HTML', 'text/html; charset=utf-8') == ('.html', 'text/html', 'interactive', HTML_LIMIT)
    assert declared_format('lab.htm', 'text/html')[2] == 'interactive'
    assert MEDIA_TYPES['image'] == {'image'} and MEDIA_TYPES['video'] == {'video'}
    assert FORMATS['.png'] == ('image/png', 'image', 10 * 1024 * 1024)
    assert FORMATS['.mp4'] == ('video/mp4', 'video', 100 * 1024 * 1024)
    target=tmp_path/'lab.html';target.write_bytes(HTML);inspect_media(target,'text/html')
    result=isolated_document(HTML)
    assert "connect-src 'none'" in result and 'onclick' in result
    assert "'wasm-unsafe-eval'" in result
    assert "'unsafe-eval'" not in result
    assert result.index('Content-Security-Policy') < result.index('<script>')
    for body in [b'<script>oops</script>', HTML.replace(b'<button', b'<iframe src="https://evil.test"></iframe><button'),
                 HTML.replace(b'<button',b'<form><input></form><button'),
                 HTML.replace(b'<title>', b'<script src="https://cdn.test/lib.js"></script><title>'),
                 HTML.replace(b'<title>',b'<meta http-equiv="refresh" content="0;url=https://evil.test"><title>'),
                 b'\xff'+HTML, b'\x00'+HTML, b'x'*(HTML_LIMIT+1)]:
        with pytest.raises(InvalidInteractive):validate_document(body)
    with pytest.raises(MediaRejected):declared_format('lab.html','image/png')
    assert ResourceStorage.checked_key('resource-uploads/'+'a'*32+'.html').endswith('.html')


def test_interactive_selection_and_existing_selection_regressions():
    assert all(result['passed'] for result in evaluate())
    candidate=dict(id='lab',title='Gravity lab',description='Explore falling objects',kind='resource',type='interactive',
        version=1,availability_state='available',concepts=['gravity'],purposes=['demonstrate'],languages=['en'],grade_min=1,grade_max=5)
    question='Show a gravity simulation'
    decision=select_recommendations([candidate],learning_need(question,''),question,'Gravity pulls objects down.',grade='Grade 1')
    assert decision['primary']['candidate_id']=='lab' and decision['display_mode']=='optional card'
    assert 'interactive' in decision['primary']['reason']
    assert select_recommendations([candidate],learning_need(question,''),question,'Gravity pulls objects down.',grade='Grade 8')['primary'] is None


def test_cloud_html_is_bounded_private_and_never_redirected(monkeypatch):
    config=Settings(_env_file=None,environment='test',resource_storage_backend='supabase',
                    supabase_url='https://storage.example.test',supabase_secret_key='fixture-secret',resource_storage_bucket='private-fixture')
    original=httpx.Client
    status=200;content=HTML
    def handler(request):
        assert str(request.url)=='https://storage.example.test/storage/v1/object/private-fixture/resource-uploads/'+'a'*32+'.html'
        assert request.headers['authorization']=='Bearer fixture-secret'
        return httpx.Response(status,content=content,headers={'location':'https://unapproved.example.test/escape'})
    monkeypatch.setattr(httpx,'Client',lambda **kwargs:original(transport=httpx.MockTransport(handler),**kwargs))
    storage=ResourceStorage(config);key='resource-uploads/'+'a'*32+'.html'
    assert storage.read_document(key,HTML_LIMIT)==HTML
    status=302
    with pytest.raises(StorageUnavailable):storage.read_document(key,HTML_LIMIT)
    status=200;content=b'x'*(HTML_LIMIT+1)
    with pytest.raises(StorageUnavailable):storage.read_document(key,HTML_LIMIT)
    with pytest.raises(StorageUnavailable):storage.read_document('../outside.html',HTML_LIMIT)


@pytest.mark.db_integration
def test_html_upload_preview_publish_scoped_delivery_and_withdrawal():
    with TemporaryDirectory() as directory, isolated_client() as client:
        config=client.app.state.settings;config.resource_local_dir=directory;config.bff_shared_key=SecretStr('interactive-fixture-secret')
        created=client.post('/api/v1/admin/curricula',json={'code':'html-'+uuid4().hex[:10],'name':'HTML fixture'}).json();cid=created['id']
        def child(kind,parent,name):
            result=client.post('/api/v1/admin/curriculum/'+kind,json={'parent_id':parent,'name':name})
            assert result.status_code==201,result.text
            return result.json()['id']
        level=child('level',cid,'Grade 1');subject=child('subject',level,'Science');domain=child('domain',subject,'Motion')
        topic=child('topic',domain,'Gravity');leaf=child('subtopic',topic,'Falling')
        tree=client.get('/api/v1/admin/curricula/'+cid+'/tree').json()
        published=client.post('/api/v1/admin/curriculum/curriculum/'+cid+'/publish',json={'expected_version':tree['version'],'expected_draft_revision':tree['draft_revision']})
        assert published.status_code==200,published.text
        def upload(data=HTML):
            return client.post('/api/v1/admin/resources/uploads',files={'file':('lab.html',data,'text/html')})
        invalid=upload(b'<script>invalid</script>');assert invalid.status_code==422
        assert invalid.json()['error']['code']=='interactive_complete_html_required'
        oversized=upload(b'x'*(HTML_LIMIT+1));assert oversized.status_code==413
        uploaded=upload();assert uploaded.status_code==201,uploaded.text
        upload_id=uploaded.json()['upload_id']
        body={'title':'Gravity lab','type':'interactive','upload_id':upload_id,'paths':[{'topic_id':topic,'subtopic_id':leaf}],
              'rights_basis':'owned','rights_holder':'Fixture','distribution_scope':'members'}
        assert client.post('/api/v1/admin/resources',json={**body,'type':'image'}).status_code==422
        assert client.post('/api/v1/admin/resources',json={**body,'type':'video'}).status_code==422
        saved=client.post('/api/v1/admin/resources',json=body);assert saved.status_code==201,saved.text
        rid=saved.json()['id'];root='/api/v1/admin/resources/'+rid
        preview=client.get(root+'/preview');assert preview.status_code==200,preview.text
        assert preview.json()['launch_mode']=='interactive' and preview.json()['url']==''
        assert 'html_document' in preview.json() and client.get(root+'/preview-content').status_code==404
        member='/api/v1/resources/'+rid
        assert client.get(member+'/delivery').status_code==404
        assert client.post(root+'/publish',json={'expected_version':1}).status_code==422
        edited=client.patch(root,json={'expected_version':1,'accessibility_note':'Tab to Drop and press Enter. No sound.'});assert edited.status_code==200,edited.text
        pub=client.post(root+'/publish',json={'expected_version':2});assert pub.status_code==200,pub.text
        version=pub.json()['version']
        query={'topic_id':topic,'subtopic_id':leaf,'curriculum_revision':published.json()['revision'],'version':version}
        delivery=client.get(member+'/delivery',params=query);assert delivery.status_code==200,delivery.text
        assert delivery.json()['launch_mode']=='interactive' and "frame-src 'none'" in delivery.json()['html_document']
        assert client.get(member+'/content',params={'expires':9999999999,'signature':'unused'}).status_code==404
        assert client.get(member+'/delivery',params={**query,'version':1}).status_code==409
        assert client.get(member+'/delivery',params={**query,'curriculum_revision':99999}).status_code==409
        unmapped=client.patch(root,json={'expected_version':version,'paths':[]});assert unmapped.status_code==200
        assert client.get(member+'/delivery',params=query).status_code==404
        remapped=client.patch(root,json={'expected_version':unmapped.json()['version'],'paths':body['paths']});assert remapped.status_code==200
        assert client.post(root+'/unpublish',json={'expected_version':remapped.json()['version']}).status_code==200
        assert client.get(member+'/delivery').status_code==404
