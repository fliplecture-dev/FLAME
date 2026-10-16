"""Saved manual connector: reviewed resource exports and confirmed sheet-row removals.

FLAME's nonempty catalogue values remain authoritative under additive import rules.
Curriculum mappings never travel through resource sheets.
"""
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy import select
from app.modules.functional.bulk_transfer.models import GoogleSheetConnection
from app.modules.functional.bulk_transfer.service import digest,split
from app.modules.functional.bulk_transfer.google_sheets import TABS, MARKER
from app.modules.functional.bulk_transfer.errors import fail
from app.modules.functional.resources.models import Resource
from app.modules.functional.resources.router import deletion_dependencies


def sheet_text(value):
    """Compare Sheets booleans consistently without changing authored text."""
    if isinstance(value, bool):return 'TRUE' if value else 'FALSE'
    return '' if value is None else str(value)


def sheet_values(record, headers):
    """Write validation-sensitive fields with native types, not forced text."""
    result=[]
    for field in headers:
        value=record.get(field)
        if field in ('grade_min','grade_max','version') and value not in (None,''):
            result.append(int(value))
        elif field=='published' and value not in (None,''):
            result.append(sheet_text(value).upper()=='TRUE')
        else:result.append(sheet_text(value))
    return result


def sheet_cell(value):
    if isinstance(value,bool):return {'userEnteredValue':{'boolValue':value}}
    if isinstance(value,int):return {'userEnteredValue':{'numberValue':value}}
    return {'userEnteredValue':{'stringValue':value}}


def connection(db, owner, spreadsheet, create=False):
    item=db.scalar(select(GoogleSheetConnection).where(GoogleSheetConnection.spreadsheet_id==spreadsheet).with_for_update())
    if item and item.owner_subject!=owner:fail(403,"This spreadsheet is linked by another administrator. Use that connection owner to sync it.")
    if item is None and create:
        item=GoogleSheetConnection(owner_subject=owner,spreadsheet_id=spreadsheet,bindings={});db.add(item);db.flush()
    return item


def catalogue(db):
    from app.modules.functional.bulk_transfer.router import export_data
    records,_,_=export_data(db,"resources")
    for r in records:
        r['file']='' # Never publish private asset paths or signed delivery URLs to Sheets.
        r['status']='published' if r.get('published') else 'draft'
        r['published']='TRUE' if r.get('published') else 'FALSE'
        r['sync_action']='sync'
        for field in ('topic','concepts','synonyms','teaching_languages','purposes'):
            r[field]=' | '.join(split(r.get(field)))
    return {r['existing_id']:r for r in records}


def sheet_snapshot(names, grids, markers):
    return digest([names,grids,sorted((s,r,m['metadataValue']) for (s,r),m in markers.items())])


def actions(db, conn, names, grids, refs):
    records=catalogue(db);seen_ids={str(r.get('matched_id') or r['source'].get('existing_id') or '') for r in refs}
    seen_keys={r['record_key'] for r in refs};seen_markers={r['marker'] for r in refs}
    deleted=[];ambiguous=[];retirements=[]
    for ref in refs:
        if ref.get('operation') not in ('delete','retired'):continue
        row=db.get(Resource,UUID(ref['matched_id']))
        action={'resource_id':str(row.id),'title':row.title,'version':row.version,'marker':ref['marker'],
                'tab':ref['tab'],'record_key':ref['record_key'],'dependencies':deletion_dependencies(db,row),
                'reason':'deleted_in_flame' if row.deleted_at else 'marked_delete'}
        (retirements if row.deleted_at else deleted).append(action)
    for marker,binding in conn.bindings.items():
        if binding.get('retired') or binding['resource_id'] not in records:continue
        if marker in seen_markers:continue
        if binding['resource_id'] in seen_ids or binding['record_key'] in seen_keys:
            ambiguous.append(binding['title']);continue
        row=db.get(Resource,UUID(binding['resource_id']))
        deleted.append({'resource_id':str(row.id),'title':row.title,'version':row.version,'marker':marker,
            'tab':binding['tab'],'record_key':binding['record_key'],'reason':'missing_sheet_row','dependencies':deletion_dependencies(db,row)})
    if len({x['resource_id'] for x in deleted})!=len(deleted):fail(422,'The same resource has multiple deletion requests. Keep one linked row per resource.')
    deleted_ids={r['resource_id'] for r in deleted}
    append=[];updates=[]
    for rid,r in records.items():
        if rid in deleted_ids:continue
        ref=next((x for x in refs if str(x.get('matched_id') or x['source'].get('existing_id') or '')==rid or x['record_key']==r['record_key']),None)
        if ref:
            changes=[{'field':h,'before':ref['source'].get(h,''),'after':r.get(h,'')} for h in ref['headers'] if h not in ('record_key','existing_id','file','sync_action') and sheet_text(ref['source'].get(h,''))!=sheet_text(r.get(h,'')) and r.get(h) not in (None,'',[])]
            if changes:updates.append({'resource_id':rid,'marker':ref['marker'],'tab':ref['tab'],'changes':changes,'version':r['version']})
        else:
            tab=next((n for n,t in TABS.items() if t==r['type']),None)
            if tab:append.append({'resource_id':rid,'record_key':r['record_key'],'title':r['title'],'tab':tab,'marker':uuid4().hex,'version':r['version']})
    if len(refs)+len(append)>2000:fail(413,"The connected catalogue exceeds 2,000 rows. Use a smaller resource catalogue before connecting.")
    return {'connection_id':str(conn.id),'append':append,'updates':updates,'deletions':deleted,'retirements':retirements,'ambiguous':ambiguous,
        'catalogue_fingerprint':digest(records),'bindings_fingerprint':digest(conn.bindings),
        'headers':{n:[str(h).strip() for h in grids[n][0]] for n in TABS},'sheet_ids':names}


def augment_review(db, source, review):
    connector=source.get('connector')
    if not connector:return review
    conn=db.get(GoogleSheetConnection,UUID(connector['connection_id']))
    # Include current state in the token: catalogue or prior-sync changes require re-review.
    review['connector_fingerprint']=digest([catalogue(db),conn.bindings])
    review['connector_preview']=connector
    for action in connector['append']:
        review['entries'].append({'row':len(review['entries'])+2,'sheet_row':None,'tab':action['tab'],'name':action['title'],'record_key':action['record_key'],
            'operation':'export','existing_id':action['resource_id'],'errors':[],'fields_to_fill':['Export FLAME resource to Sheets'],'preserved_fields':[]})
    for action in connector['deletions']:
        if any(e.get('existing_id')==action['resource_id'] and e['operation']=='delete' for e in review['entries']):continue
        review['entries'].append({'row':len(review['entries'])+2,'sheet_row':None,'tab':action['tab'],'name':action['title'],'record_key':'','existing_id':action['resource_id'],
            'operation':'delete','errors':[],'preserved_fields':[],'fields_to_fill':['Delete from FLAME after explicit confirmation; media/history retained']})
    if connector['ambiguous']:
        review['entries'].append({'row':len(review['entries'])+2,'name':'Row tracking conflict','record_key':'','operation':'invalid','errors':['Tracking was removed or replaced for: '+', '.join(connector['ambiguous'])+'. Restore row metadata or resolve the source before deletion can be reviewed.']})
    review['counts']={op:sum(e['operation']==op for e in review['entries']) for op in ('add','merge','unchanged','invalid','export','delete','retired')}
    review['total']=len(review['entries'])
    return review


def export_writeback(client, db, source, ids, expected_records):
    """One atomic Google batch for append+row tracking; existing rows use metadata filters.

    Response-loss retries recognize previously exported rows by their reserved markers.
    """
    names,grids,markers=client.read();conn_info=source['connector']
    if not set(getattr(client,'tracking_cleanup',[]))<=set(source.get('tracking_cleanup',[])):fail(409,'New tracking conflicts appeared after preview. Resolve them before retrying.')
    current_by_marker={m['metadataValue']:(s,r,m) for (s,r),m in markers.items()}
    expected_markers={r['marker'] for r in source['rows']}|{a['marker'] for a in conn_info['append']}
    header_requests=[];target_headers={}
    for tab in TABS:
        headers=[str(h).strip() for h in grids.get(tab,[[]])[0]]
        original=conn_info['headers'][tab]
        target_headers[tab]=original if 'sync_action' in original else original+['sync_action']
        if names.get(tab)!=conn_info['sheet_ids'][tab] or headers not in (original,target_headers[tab]):fail(409,"Connected sheet tabs/columns changed. Restore them before retrying this saved sync.")
        if 'sync_action' not in headers:
            col=len(headers);capacity=getattr(client,'grid_columns',{}).get(names[tab],60)
            if col+1>60:fail(413,'No space for the deletion column. Trim unused columns before retrying.')
            if col+1>capacity:header_requests.append({'appendDimension':{'sheetId':names[tab],'dimension':'COLUMNS','length':col+1-capacity}})
            header_requests.append({'updateCells':{'start':{'sheetId':names[tab],'rowIndex':0,'columnIndex':col},
                'rows':[{'values':[{'userEnteredValue':{'stringValue':'sync_action'},'userEnteredFormat':{'textFormat':{'bold':True}},
                    'note':'Blank/sync keeps the resource. Set delete to request reviewed deletion while preserving key/ID. FLAME writes deleted after confirmation.'}]}],
                'fields':'userEnteredValue,userEnteredFormat.textFormat.bold,note'}})
            header_requests.append({'setDataValidation':{'range':{'sheetId':names[tab],'startRowIndex':1,'startColumnIndex':col,'endColumnIndex':col+1},
                'rule':{'condition':{'type':'ONE_OF_LIST','values':[{'userEnteredValue':v} for v in ('sync','delete','deleted')]},
                'strict':True,'showCustomUi':True,'inputMessage':'Set delete to request reviewed deletion. Keep key/ID. FLAME writes deleted after confirmation.'}}})
        for row,cells in enumerate(grids[tab][1:],2):
            if not any(c not in (None,'') for c in cells):continue
            item=markers.get((names[tab],row))
            if not item or item['metadataValue'] not in expected_markers:fail(409,"A sheet row was added or its identity changed after preview. Resolve the source before retrying; FLAME data is retained.")
    data=[];bindings={};requests=[]
    values=sheet_values
    for ref in source['rows']:
        rid=ids.get(ref['record_key']) or ref.get('matched_id') or str(ref['source'].get('existing_id') or '')
        record=expected_records.get(rid)
        if not record:continue
        located=current_by_marker.get(ref['marker'])
        if not located or located[0]!=ref['sheet_id']:fail(409,"A saved sync source row was removed. Restore it before retrying.")
        _,row,m=located;headers=target_headers[ref['tab']];cells=grids[ref['tab']][row-1]
        current={h:c for h,c in zip(headers,cells)};expected=dict(record,record_key=ref['record_key'],existing_id=rid)
        expected.setdefault('sync_action','sync')
        for h in headers:
            if h=='type' and current.get(h,'')=='':continue  # Blank type was inferred from the tab at preview.
            if sheet_text(current.get(h,'')) not in (sheet_text(ref['source'].get(h,'')),sheet_text(expected.get(h,''))):fail(409,"Sheet content changed after preview. Resolve the row conflict before retrying.")
        data.append({'dataFilter':{'developerMetadataLookup':{'metadataId':m['metadataId']}},'majorDimension':'ROWS','values':[values(expected,headers)]})
        bindings[ref['marker']]={'resource_id':rid,'record_key':ref['record_key'],'tab':ref['tab'],'title':record['title'],'retired':record.get('sync_action')=='deleted'}
    # Existing row writes can be retried even after their values have reached FLAME state.
    # Add headers only after every existing row is checked. A retry accepts the
    # exact appended header, so successful partial writes cannot duplicate it.
    if header_requests:client.call('POST',':batchUpdate',json={'requests':header_requests})
    if data:
        result=client.call('POST','/values:batchUpdateByDataFilter',json={'valueInputOption':'RAW','data':data})
        if result.get('totalUpdatedCells')!=sum(len(d['values'][0]) for d in data):fail(409,"Not all resource cells were confirmed. Retry the saved sheet update.")
    next_row={tab:len(grids[tab]) for tab in TABS}
    grouped={tab:[] for tab in TABS}
    for action in conn_info['append']:
        rid=action['resource_id'];record={**expected_records[rid]};record.setdefault('sync_action','sync');tab=action['tab'];headers=target_headers[tab]
        if action['marker'] in current_by_marker:
            sheet,row,_=current_by_marker[action['marker']]
            if sheet!=names[tab] or [sheet_text(v) for v in values(record,headers)]!=[sheet_text(v) for v in grids[tab][row-1]]:fail(409,"A previously exported row changed. Resolve it before retrying.")
        else:grouped[tab].append((action,record))
        bindings[action['marker']]={'resource_id':rid,'record_key':record['record_key'],'tab':tab,'title':record['title']}
    for tab,items in grouped.items():
        if not items:continue
        start=next_row[tab];headers=target_headers[tab];end=start+len(items)
        grid_rows=getattr(client,'grid_rows',{}).get(names[tab],1000)
        if end>grid_rows:requests.append({'appendDimension':{'sheetId':names[tab],'dimension':'ROWS','length':end-grid_rows}})
        requests.append({'updateCells':{'start':{'sheetId':names[tab],'rowIndex':start,'columnIndex':0},'fields':'userEnteredValue',
            'rows':[{'values':[sheet_cell(v) for v in values(record,headers)]} for _,record in items]}})
        for index,(action,_) in enumerate(items):requests.append({'createDeveloperMetadata':{'developerMetadata':{'metadataKey':MARKER,'metadataValue':action['marker'],'visibility':'DOCUMENT',
            'location':{'dimensionRange':{'sheetId':names[tab],'dimension':'ROWS','startIndex':start+index,'endIndex':start+index+1}}}}})
    requests.extend({'deleteDeveloperMetadata':{'dataFilter':{'developerMetadataLookup':{'metadataId':mid}}}} for mid in getattr(client,'tracking_cleanup',[]))
    if requests:client.call('POST',':batchUpdate',json={'requests':requests})
    conn=db.get(GoogleSheetConnection,UUID(conn_info['connection_id']))
    conn.bindings=bindings;conn.last_synced_at=datetime.now(timezone.utc)
