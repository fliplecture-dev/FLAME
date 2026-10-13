"""Explicit deletion/tombstones; no title-based destructive identity matching."""
from uuid import UUID
from sqlalchemy import select
from app.modules.bulk_transfer.models import BulkIdentity,GoogleSheetConnection
from app.modules.resources.models import Resource


def lifecycle_entries(db,payload):
    source=payload['sheets'];conn=db.get(GoogleSheetConnection,UUID(source['connection_id'])) if source.get('connection_id') else None
    keys={r['record_key'] for r in source['rows']}
    identities={i.record_key:i for i in db.scalars(select(BulkIdentity).where(BulkIdentity.kind=='resources',BulkIdentity.record_key.in_(keys)))}
    ids={i.entity_id for i in identities.values()}
    for raw,ref in zip(payload['records'],source['rows']):
        bound=(conn.bindings or {}).get(ref['marker']) if conn else None
        for value in (raw.get('existing_id'),bound['resource_id'] if bound else None):
            try:
                if value:ids.add(UUID(str(value)))
            except (ValueError,TypeError):pass
    resources={r.id:r for r in db.scalars(select(Resource).where(Resource.id.in_(ids)))}
    normal=[];special={}
    for raw,ref in zip(payload['records'],source['rows']):
        action=str(ref['source'].get('sync_action') or 'sync').strip().lower()
        rid=raw.get('existing_id');bound=(conn.bindings or {}).get(ref['marker']) if conn else None
        errors=[];row=None
        try:
            if rid:
                row=resources.get(UUID(str(rid)))
                if row is None:errors.append('Existing FLAME resource ID was not found. Preserve the original identifier.')
            identity=identities.get(ref['record_key'])
            if identity:
                keyed=resources.get(identity.entity_id)
                if row and keyed and row.id!=keyed.id:errors.append('Record key and existing ID identify different resources.')
                row=row or keyed
            if bound:
                linked=resources.get(UUID(bound['resource_id']))
                if row and linked and row.id!=linked.id:errors.append('This tracked row belongs to another resource. Preserve its linked identifiers.')
                if ref['source'].get('record_key') and str(ref['source']['record_key'])!=bound['record_key']:errors.append('Preserve this linked row’s record key before syncing or deleting.')
                row=row or linked
        except (ValueError,TypeError):errors.append('Use a valid existing FLAME ID for deletion.')
        if action not in ('sync','delete','deleted'):errors.append('sync_action must be sync, delete or deleted.')
        special_row=action!='sync' or row is not None and row.deleted_at is not None
        if special_row and conn is None:errors.append('Use the saved resource connector for deletion or deleted-row tracking.')
        if not special_row and not errors:
            clean={k:v for k,v in raw.items() if k!='sync_action'};normal.append(clean);continue
        if special_row and not row:errors.append('Deletion needs an existing resource ID, registered key or successfully linked row; a title is not sufficient.')
        if row and row.type!=raw['type']:errors.append('Move this linked row to its correct media-type tab before deleting.')
        if action=='deleted' and row and row.deleted_at is None:errors.append('deleted is written by FLAME after deletion. Use delete to request deletion.')
        errors+=ref['errors']
        operation='invalid' if errors else 'retired' if row.deleted_at else 'delete'
        special[raw['_row']]={'row':raw['_row'],'name':row.title if row else raw.get('title','Deletion request'),'record_key':ref['record_key'],
            'existing_id':str(row.id) if row else None,'version':row.version if row else None,'operation':operation,'errors':errors}
    return normal,special


def bind_client(client,db,source=None,conn=None):
    cid=(source.get('connection_id') or source.get('connector',{}).get('connection_id')) if source else None
    if conn is None and cid:
        conn=db.get(GoogleSheetConnection,UUID(cid))
    client.bindings=conn.bindings if conn else {}


def retired_record(db,row,key):
    from app.modules.bulk_transfer.service import snapshot
    from app.modules.bulk_transfer.service import split
    r=snapshot(db,'resources',row);education=r.get('learning_metadata',{})
    r.update(existing_id=str(row.id),record_key=key,file='',sync_action='deleted',status='deleted',published='FALSE',availability='unavailable')
    for field in ('topic','concepts','synonyms','teaching_languages','purposes'):
        r[field]=' | '.join(split(education.get('topic_labels' if field=='topic' else 'languages' if field=='teaching_languages' else field)))
    for field in ('grade_min','grade_max'):r[field]=education.get(field)
    return r


def outgoing_records(db,source):
    from app.modules.bulk_transfer.sheet_connector import catalogue
    records=catalogue(db)
    for action in source['connector']['deletions']+source['connector'].get('retirements',[]):
        row=db.get(Resource,UUID(action['resource_id']))
        if row and row.deleted_at:records[str(row.id)]=retired_record(db,row,action.get('record_key') or str(row.id))
    return records
