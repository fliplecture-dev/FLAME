from copy import deepcopy
from uuid import UUID
import pytest
from app.modules.bulk_transfer.google_sheets import SheetsClient,MARKER
from app.modules.bulk_transfer.errors import BulkFailure
from app.modules.resources.models import Resource,ResourceTopic
from test_curriculum_workspace import isolated_client
from test_google_sheets_sync import FakeSheets,install


def test_explicit_and_flame_deletion_tombstones_and_retries(monkeypatch):
    import app.modules.bulk_transfer.sheet_connector as connector
    original=connector.catalogue
    fake=FakeSheets();install(monkeypatch,fake)
    with isolated_client() as client:
        client.app.state.settings.resource_allowed_hosts='media.example.test'
        from sqlalchemy import select
        with client.app.state.database.session() as db:old={str(x) for x in db.scalars(select(Resource.id))}
        monkeypatch.setattr(connector,'catalogue',lambda db:{k:v for k,v in original(db).items() if k not in old})
        root='/api/v1/admin/bulk/google-sheets/'
        def preview():
            response=client.post(root+'preview',json={'spreadsheet':fake.ident});assert response.status_code==200,response.text
            return response.json()['job']
        def commit(job,ids=None):return client.post(root+job['id']+'/commit',json={'confirm':True,'confirm_sheet_updates':True,'preview_token':job['preview_token'],'confirm_delete_ids':ids or []})
        first=preview();assert first['counts']['add']==3
        assert commit(first).json()['writeback']=='completed'
        assert all(grid[0][-1]=='sync_action' and grid[1][-1]=='sync' for grid in fake.grids.values())
        image_id=fake.grids['Image'][1][1];video_id=fake.grids['Video'][1][1];game_id=fake.grids['Interactive'][1][1]
        from test_bulk_transfer import path_fixture
        topic,leaf,subject=path_fixture(client)
        with client.app.state.database.session() as db,db.begin():db.add(ResourceTopic(resource_id=UUID(image_id),topic_id=UUID(topic),subtopic_id=UUID(leaf)))
        fake.grids['Image'][1][-1]='delete'
        deletion=preview();assert deletion['counts']['delete']==1 and deletion['counts']['invalid']==0
        assert commit(deletion).status_code==422
        assert client.get('/api/v1/admin/resources/'+image_id).status_code==200
        fake.grids['Image'][1][-1]='sync'
        assert commit(deletion,[image_id]).status_code==409
        assert client.get('/api/v1/admin/resources/'+image_id).status_code==200
        assert client.post('/api/v1/admin/bulk/imports/'+deletion['id']+'/cancel',json={}).status_code==200
        fake.grids['Image'][1][-1]='delete';deletion=preview()
        original_read=fake.read
        def read_failure():raise BulkFailure(503,'Fixture read failure')
        fake.read=read_failure;result=commit(deletion,[image_id]);assert result.status_code==503
        assert client.get('/api/v1/admin/resources/'+image_id).status_code==200
        fake.read=original_read
        # Fail only the post-commit write so the confirmed FLAME deletion is retained.
        original_call=fake.call
        def write_failure(method,suffix,**kwargs):
            if suffix=='/values:batchUpdateByDataFilter':raise BulkFailure(503,'Fixture write failure')
            return original_call(method,suffix,**kwargs)
        fake.call=write_failure
        result=commit(deletion,[image_id]);assert result.status_code==200,result.text
        assert result.json()['writeback']=='pending'
        assert client.get('/api/v1/admin/resources/'+image_id).status_code==404
        with client.app.state.database.session() as db:
            row=db.get(Resource,UUID(image_id));assert row.deletion_snapshot and row.external_url and not row.published
            assert not db.scalars(select(ResourceTopic).where(ResourceTopic.resource_id==row.id)).all()
        fake.call=original_call
        retry=client.post(root+deletion['id']+'/writeback',json={});assert retry.status_code==200 and retry.json()['writeback']=='completed',retry.text
        assert fake.grids['Image'][1][-1]=='deleted' and fake.grids['Image'][1][1]==image_id
        repeat=preview();assert repeat['counts']['retired']==1 and repeat['counts']['delete']==0 and repeat['counts']['add']==0
        assert commit(repeat).json()['writeback']=='completed'
        # Ordinary Resource Library deletion is mirrored without re-importing the linked row.
        resource=client.get('/api/v1/admin/resources/'+video_id).json()
        removed=client.post('/api/v1/admin/resources/'+video_id+'/delete',json={'expected_version':resource['version'],'confirm_resource_id':video_id});assert removed.status_code==200,removed.text
        mirrored=preview();assert mirrored['counts']['retired']==2 and mirrored['counts']['invalid']==0
        assert commit(mirrored).json()['writeback']=='completed';assert fake.grids['Video'][1][-1]=='deleted'
        # Purging an already-deleted tombstone from the Sheet cannot delete another resource.
        fake.grids['Image'].pop();fake.markers.pop((1,2))
        purged=preview();assert purged['counts']['delete']==0 and purged['counts']['retired']==1
        assert commit(purged).json()['writeback']=='completed'
        fake.grids['Interactive'][1][-1]='deleted'
        forged=preview();assert forged['counts']['invalid']==1
        assert commit(forged).status_code==422
        assert client.get('/api/v1/admin/resources/'+game_id).status_code==200


def test_duplicate_marker_repair_requires_unambiguous_identity():
    client=object.__new__(SheetsClient)
    a={'metadataId':100,'metadataKey':MARKER,'metadataValue':'a','location':{'dimensionRange':{'sheetId':1,'dimension':'ROWS','startIndex':1,'endIndex':2}}}
    b={**deepcopy(a),'metadataId':101,'metadataValue':'b'}
    client.bindings={'a':{'resource_id':'id-a','record_key':'key-a'},'b':{'resource_id':'id-b','record_key':'key-b'}}
    values=[a,b]
    def call(method,suffix='',**kwargs):
        if not suffix:return {'sheets':[{'properties':{'sheetId':1,'title':'Image','gridProperties':{'columnCount':3}}}]}
        if suffix=='/values:batchGet':return {'valueRanges':[{'values':[['record_key','existing_id','title'],['key-a','id-a','Kept row']]}]}
        return {'matchedDeveloperMetadata':[{'developerMetadata':v} for v in values]}
    client.call=call
    _,_,markers=client.read();assert markers[(1,2)]['metadataValue']=='a' and client.tracking_cleanup==[101]
    # An unknown second identity is never silently discarded.
    values[1]['metadataValue']='unknown'
    with pytest.raises(BulkFailure,match='cannot be resolved safely'):client.read()
    values[1]['metadataValue']='a'
    _,_,markers=client.read();assert markers[(1,2)]['metadataId']==100 and client.tracking_cleanup==[101]


def test_automatic_action_column_is_idempotent_after_partial_write_failure():
    from types import SimpleNamespace
    from uuid import uuid4
    from app.modules.bulk_transfer.google_sheets import collect
    from app.modules.bulk_transfer.sheet_connector import export_writeback
    fake=FakeSheets()
    rows,refs,issues,requests=collect(*fake.read(),reserve=True)
    fake.mark(requests)
    source={'rows':refs,'connector':{'connection_id':str(uuid4()),'sheet_ids':fake.names.copy(),
            'headers':{tab:grid[0].copy() for tab,grid in fake.grids.items()},'append':[]}}
    ids={r['record_key']:str(uuid4()) for r in rows}
    records={ids[r['record_key']]:{**r,'existing_id':ids[r['record_key']],'sync_action':'sync'} for r in rows}
    conn=SimpleNamespace(bindings={},last_synced_at=None)
    db=SimpleNamespace(get=lambda *args:conn)
    original=fake.call
    def partial_failure(method,suffix,**kwargs):
        if suffix=='/values:batchUpdateByDataFilter':raise BulkFailure(503,'Fixture values failure after headers')
        return original(method,suffix,**kwargs)
    fake.call=partial_failure
    with pytest.raises(BulkFailure):export_writeback(fake,db,source,ids,records)
    assert all(grid[0].count('sync_action')==1 for grid in fake.grids.values())
    fake.call=original
    export_writeback(fake,db,source,ids,records)
    assert all(grid[0].count('sync_action')==1 and grid[1][-1]=='sync' for grid in fake.grids.values())
    export_writeback(fake,db,source,ids,records)
    assert all(grid[0].count('sync_action')==1 for grid in fake.grids.values())
