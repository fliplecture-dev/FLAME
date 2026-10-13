"""Persistent connector, confirmed deletes and FLAME exports use rollback-only fixtures."""
from uuid import UUID
from sqlalchemy import select
from app.modules.resources.models import Resource
from test_curriculum_workspace import isolated_client
from test_google_sheets_sync import FakeSheets,install


def test_sheet_output_uses_native_numbers_and_booleans_without_prefixes():
    from app.modules.bulk_transfer.sheet_connector import sheet_values,sheet_cell,sheet_text
    headers=['record_key','existing_id','title','grade_min','grade_max','version','published','status']
    record=dict(record_key='00123',existing_id='uuid',title="=Text, not a formula",grade_min=0,grade_max='3',version=4,published='FALSE',status='draft')
    values=sheet_values(record,headers)
    assert values==['00123','uuid','=Text, not a formula',0,3,4,False,'draft']
    assert sheet_cell(values[3])=={'userEnteredValue':{'numberValue':0}}
    assert sheet_cell(values[6])=={'userEnteredValue':{'boolValue':False}}
    assert sheet_cell(values[2])=={'userEnteredValue':{'stringValue':'=Text, not a formula'}}
    assert sheet_text(False)=='FALSE'
    assert sheet_values({'title':"'Quoted title",'grade_min':None},['title','grade_min'])==["'Quoted title",'']


def test_existing_video_sync_retains_source_during_provider_outage(monkeypatch):
    from app.modules.bulk_transfer import service
    from fastapi import HTTPException
    from uuid import uuid4
    calls=[]
    def unavailable(url,config):
        calls.append(url)
        raise HTTPException(422,{'code':'external_video_verification_failed','field':'external_url'})
    monkeypatch.setattr(service,'inspect_video',unavailable)
    with isolated_client() as client,client.app.state.database.session() as db:
        row=Resource(id=uuid4(),title='Retained YouTube video',type='video',external_url='https://www.youtube.com/watch?v=IBedXUq0oVo')
        db.add(row);db.flush()
        record={'_row':2,'record_key':'retained-video','existing_id':str(row.id),'title':row.title,'type':'video','external_url':row.external_url}
        payload={'records':[record],'mappings':[],'uploads':{}}
        review=service.plan(db,client.app.state.settings,'resources',payload)
        assert review['counts']['unchanged']==1 and not calls
        record['external_url']='https://www.youtube.com/watch?v=abcdef12345'
        review=service.plan(db,client.app.state.settings,'resources',payload)
        assert review['counts']['invalid']==1 and len(calls)==1


def test_connector_initial_export_repeat_new_rows_and_confirmed_deletion(monkeypatch):
    import app.modules.bulk_transfer.sheet_connector as connector
    original=connector.catalogue
    fake=FakeSheets();install(monkeypatch,fake)
    for grid in fake.grids.values():
        grid[0].extend(['grade_min','grade_max','version','published','status'])
        for row in grid[1:]:row.extend(['']*5)
    with isolated_client() as client:
        client.app.state.settings.resource_allowed_hosts='media.example.test'
        with client.app.state.database.session() as db:old={str(x) for x in db.scalars(select(Resource.id)).all()}
        monkeypatch.setattr(connector,'catalogue',lambda db:{k:v for k,v in original(db).items() if k not in old})
        direct=client.post('/api/v1/admin/resources',json={'title':'Connector FLAME game','type':'interactive'});assert direct.status_code in (200,201),direct.text
        rid=direct.json()['id']
        def preview():
            result=client.post('/api/v1/admin/bulk/google-sheets/preview',json={'spreadsheet':fake.ident,'connector':True});assert result.status_code==200,result.text;return result.json()['job']
        def commit(job,delete_ids=None):
            return client.post('/api/v1/admin/bulk/google-sheets/'+job['id']+'/commit',json={'confirm':True,'preview_token':job['preview_token'],'confirm_sheet_updates':True,'confirm_delete_ids':delete_ids or []})
        job=preview();assert job['counts']['add']==3 and job['counts']['export']==1
        fake.offline=True
        saved=commit(job);assert saved.status_code==200,saved.text;assert saved.json()['writeback']=='pending',saved.text
        fake.offline=False
        retry=client.post('/api/v1/admin/bulk/google-sheets/'+job['id']+'/writeback',json={})
        assert retry.status_code==200 and retry.json()['writeback']=='completed',retry.text
        assert len(fake.grids['Interactive'])==3
        assert isinstance(fake.grids['Interactive'][2][7],int)
        assert fake.grids['Interactive'][2][8] is False
        for grid in fake.grids.values():
            assert grid[0].count('sync_action')==1
            assert all(row[-1]=='sync' for row in grid[1:])
        connected=client.get('/api/v1/admin/bulk/google-sheets/connections').json();assert len(connected['items'])==1 and connected['items'][0]['last_synced_at']
        again=preview();assert again['counts']['add']==0 and again['counts']['export']==0 and again['counts']['delete']==0
        assert commit(again).json()['writeback']=='completed'
        # Clearing identifiers does not create a second resource for a tracked row.
        fake.grids['Interactive'][2][0]='';fake.grids['Interactive'][2][1]=''
        recovered=preview();assert recovered['counts']['add']==0 and recovered['counts']['export']==0
        assert commit(recovered).json()['writeback']=='completed'
        assert fake.grids['Interactive'][2][1]==rid
        # FLAME field edits are mirrored into the reviewed sheet update.
        row=client.get('/api/v1/admin/resources/'+rid).json()
        changed=client.patch('/api/v1/admin/resources/'+rid,json={'expected_version':row['version'],'description':'Changed in FLAME'});assert changed.status_code==200,changed.text
        update=preview();assert update['connector_preview']['updates']
        assert commit(update).json()['writeback']=='completed'
        assert fake.grids['Interactive'][2][4]=='Changed in FLAME'
        # Removal is scoped to previously bound rows; no missing-tab/truncation guessing.
        fake.grids['Interactive'].pop();fake.markers.pop((3,3))
        removed=preview();assert removed['counts']['delete']==1
        assert commit(removed).status_code==422
        assert client.get('/api/v1/admin/resources/'+rid).status_code==200
        confirmed=commit(removed,[rid]);assert confirmed.status_code==200,confirmed.text
        assert confirmed.json()['result']['deleted']==1 and confirmed.json()['writeback']=='completed'
        assert client.get('/api/v1/admin/resources/'+rid).status_code==404
        assert commit(removed,[rid]).json()['result']['deleted']==1
        final=preview();assert final['counts']['delete']==0 and final['counts']['export']==0


def test_connector_cancel_and_missing_tabs_never_delete(monkeypatch):
    fake=FakeSheets();install(monkeypatch,fake)
    with isolated_client() as client:
        client.app.state.settings.resource_allowed_hosts='media.example.test'
        fake.names.pop('Video')
        result=client.post('/api/v1/admin/bulk/google-sheets/preview',json={'spreadsheet':fake.ident})
        assert result.status_code==200 and result.json()['job'] is None
        assert any(i['tab']=='Video' and i['severity']=='error' for i in result.json()['sheet_issues'])


def test_connector_rejects_out_of_range_rows_and_ambiguous_tracking(monkeypatch):
    from app.modules.bulk_transfer.google_sheets import collect
    fake=FakeSheets()
    fake.grids['Interactive'] += [[]]*2000
    assert any(i['severity']=='error' and i['tab']=='Interactive' for i in collect(*fake.read(),reserve=True)[2])
