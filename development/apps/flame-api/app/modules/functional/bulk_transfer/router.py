"""Protected preview/confirm/replay and workbook/package downloads."""
import json
from datetime import datetime, timezone, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Annotated, Literal
from uuid import UUID, uuid5
from zipfile import ZipFile, ZIP_DEFLATED
import httpx
from fastapi import APIRouter, Depends, File, Request, UploadFile, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select, text
from starlette.datastructures import Headers
from app.modules.functional.bulk_transfer.errors import fail
from app.modules.functional.identity.dependencies import require_admin
from app.modules.functional.identity.import_profiles import lock_profile_email
from app.modules.functional.identity.models import StudentProfile, AdminRole
from app.modules.functional.bulk_transfer.models import BulkImport, BulkIdentity
from app.modules.functional.bulk_transfer.workbooks import KINDS, MAX_PACKAGE, decode, workbook, EDUCATION
from app.modules.functional.bulk_transfer.service import MODELS, plan, apply, digest, snapshot, split
from app.modules.functional.resources.router import upload_resource, store_upload
from app.modules.functional.resources.models import ResourceUpload, Resource
from app.modules.functional.activity_kits.models import ActivityKit
from app.modules.functional.resources.storage import ResourceStorage
from app.modules.functional.resources.validation import FORMATS
from app.modules.functional.resources.service import path_choices
from app.modules.functional.curriculum.models import Curriculum

router = APIRouter(prefix="/api/v1/admin/bulk", tags=["admin-bulk-transfer"])
Admin = Annotated[dict, Depends(require_admin)]
Kind = Literal["resources", "teachers", "students", "activity-kits"]


class Confirm(BaseModel):
    preview_token: str = Field(min_length=64, max_length=64)
    confirm: bool
    confirm_sheet_updates: bool = False
    confirm_delete_ids: list[UUID] = Field(default_factory=list, max_length=2000)


def principal_subject(db, principal):
    row = db.get(StudentProfile, UUID(principal["id"]))
    if row is None: fail(401, "Administrator profile is unavailable.")
    return row.auth_subject


def locked_job(db, job_id, owner):
    job = db.scalar(select(BulkImport).where(BulkImport.id == job_id).with_for_update())
    if job is None or job.owner_subject != owner: fail(404, "Bulk import not found.")
    return job


def response(job):
    # Normalized bodies are retained server-side; preview exposes only review information.
    return {"id": str(job.id), "kind": job.kind, "filename": job.filename, "status": job.status,
        "preview_token": job.token, "counts": job.preview["counts"], "total": job.preview["total"],
        "rows": [{k: v for k, v in e.items() if k in {"row", "record_key", "name", "operation", "existing_id", "errors", "preserved_fields", "tab", "sheet_row", "conflicts"}} |
            {"errors": e.get("errors") or [], "preserved_fields": e.get("preserved_fields") or [], "fields_to_fill": e.get('fields_to_fill',list(e.get("updates", {}))), "mappings_to_add": len(e.get("mapping_additions", []))} for e in job.preview["entries"]], "result": {k:v for k,v in job.result.items() if k!='sheet_records'} if job.result else None,
        **({'connector_preview':job.preview['connector_preview']} if 'connector_preview' in job.preview else {}),
        **({"sheet_issues": job.payload["sheets"]["issues"], "spreadsheet_id": job.payload["sheets"]["spreadsheet_id"], "writeback": (job.result or {}).get("writeback", "not_started")} if "sheets" in job.payload else {})}


def review_payload(db, config, job):
    if "sheets" in job.payload:
        from app.modules.functional.bulk_transfer.google_sheets import sheet_plan
        return sheet_plan(db, config, job.payload)
    return plan(db, config, job.kind, job.payload)


@router.post("/{kind}/preview")
def preview(request: Request, principal: Admin, kind: Kind, file: UploadFile = File(...)):
    return preview_file(request, principal, kind, file)


def preview_file(request, principal, kind, file, *, reserved_id=None):
    database, config = request.app.state.database, request.app.state.settings
    if reserved_id:
        with database.session() as db:
            existing = db.get(BulkImport, reserved_id)
            if existing:
                if existing.owner_subject != principal_subject(db, principal) or existing.kind != kind:
                    fail(404, "Bulk import not found.")
                return response(existing)
    content = file.file.read(MAX_PACKAGE + 1)
    if len(content) > MAX_PACKAGE: fail(413, "Import exceeds 120 MiB.")
    payload, assets = decode(kind, file.filename or "", content)
    payload["asset_names"] = list(assets); payload["uploads"] = {}
    database, config = request.app.state.database, request.app.state.settings
    with database.session() as db, db.begin():
        owner = principal_subject(db, principal)
        review = plan(db, config, kind, payload)
    # Reuse upload inspection/storage/ownership; no media conversion or public delivery.
    staged = []
    try:
        if not review["counts"]["invalid"]:
            for entry in review["entries"]:
                for name in entry.get("files", []):
                    asset_key = entry["record_key"] + "::" + name
                    if asset_key in payload["uploads"]: continue
                    suffix = Path(name).suffix.lower()
                    if suffix not in FORMATS: fail(422, "Unsupported bundled media: " + name)
                    upload = UploadFile(BytesIO(assets[name]), filename=Path(name).name, headers=Headers({"content-type": FORMATS[suffix][0]}))
                    saved = (store_upload(request, principal, upload, reserved_id=uuid5(reserved_id, asset_key))
                             if reserved_id else upload_resource(request, principal, upload))
                    staged.append(saved["upload_id"]); payload["uploads"][asset_key] = saved["upload_id"]
        with database.session() as db, db.begin():
            review = plan(db, config, kind, payload)
            job = BulkImport(kind=kind, owner_subject=owner, filename=Path((file.filename or "import.xlsx").replace("\\", "/")).name[:255], payload=payload,
                preview=review, token=digest(review))
            if reserved_id:
                job.id = reserved_id
            db.add(job); db.flush(); result = response(job)
        return result
    except Exception:
        # A concurrent direct completion may have committed these same reserved
        # asset IDs. Preserve them for receipt replay or unused-upload cleanup.
        if not reserved_id:
            with database.session() as db, db.begin(): cleanup(db, config, staged, owner)
        raise


@router.get("/imports/{job_id}")
def detail(request: Request, principal: Admin, job_id: UUID):
    with request.app.state.database.session() as db, db.begin():
        return response(locked_job(db, job_id, principal_subject(db, principal)))


@router.post("/imports/{job_id}/review")
def refresh(request: Request, principal: Admin, job_id: UUID):
    with request.app.state.database.session() as db, db.begin():
        job = locked_job(db, job_id, principal_subject(db, principal))
        if job.status != "review": fail(409, "This import is already completed or cancelled.")
        if datetime.now(timezone.utc) - job.created_at > timedelta(hours=24): fail(409, "Preview expired. Cancel it and upload a fresh package.")
        job.preview = review_payload(db, request.app.state.settings, job); job.token = digest(job.preview)
        return response(job)


@router.post("/imports/{job_id}/commit")
def commit(request: Request, principal: Admin, job_id: UUID, body: Confirm):
    with request.app.state.database.session() as db, db.begin():
        owner = principal_subject(db, principal); job = locked_job(db, job_id, owner)
        if not body.confirm: fail(422, "Confirm the reviewed additive import.")
        if job.status == "completed": return response(job)
        if job.status != "review": fail(409, "Import was cancelled.")
        if datetime.now(timezone.utc) - job.created_at > timedelta(hours=24): fail(409, "Preview expired. Cancel it and upload a fresh package.")
        if "sheets" in job.payload:
            from app.modules.functional.bulk_transfer.google_sheets import SheetsClient, recheck
            client=SheetsClient(request.app.state.settings, job.payload["sheets"]["spreadsheet_id"])
            source=job.payload['sheets']
            from app.modules.functional.bulk_transfer.sheet_lifecycle import bind_client
            bind_client(client,db,source)
            if 'connector' in source:
                from app.modules.functional.bulk_transfer.sheet_connector import sheet_snapshot
                if not body.confirm_sheet_updates:fail(422,'Confirm the reviewed FLAME-to-Sheets data updates.')
                expected={x['resource_id'] for x in source['connector']['deletions']}
                if {str(x) for x in body.confirm_delete_ids}!=expected:fail(422,'Explicitly confirm every removed resource listed in this sync preview.')
                if sheet_snapshot(*client.read())!=source['sheet_snapshot']:fail(409,'Google Sheets changed after preview. Cancel and validate a fresh comparison; nothing was saved.')
                if getattr(client,'tracking_cleanup',[])!=source.get('tracking_cleanup',[]):fail(409,'Sheet tracking changed after preview. Validate again before confirming.')
            recheck(client, source)
        db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": 610072600 + KINDS.index(job.kind)})
        if job.kind == "students":
            for email in sorted({str(r.get("email", "")).strip().lower() for r in job.payload["records"]}):
                lock_profile_email(db, email)
        # Lock catalogue rows before taking the new snapshot, including edits from ordinary screens.
        db.scalars(select(MODELS[job.kind]).with_for_update()).all()
        latest = review_payload(db, request.app.state.settings, job)
        if body.preview_token != job.token or digest(latest) != job.token:
            fail(409, "The catalogue or mappings changed after preview. Nothing was imported. Review latest comparison and confirm again; the workbook and staged files are retained.")
        if latest["counts"]["invalid"]: fail(422, "Correct the invalid rows before importing. Nothing was saved.")
        incoming={**latest,'entries':[e for e in latest['entries'] if e['operation'] in ('add','merge','unchanged')]}
        job.result = apply(db, request.app.state.settings, job.kind, incoming, owner); job.status = "completed"
        if "sheets" in job.payload: job.result = {**job.result, "writeback": "pending"}
        if job.payload.get('sheets',{}).get('connector'):
            from app.modules.functional.resources.router import DeleteResource,delete_resource_in_session
            from app.modules.functional.bulk_transfer.sheet_connector import catalogue
            removed=job.payload['sheets']['connector']['deletions']
            for action in removed:
                delete_resource_in_session(db,principal,UUID(action['resource_id']),DeleteResource(expected_version=action['version'],confirm_resource_id=action['resource_id']))
            from app.modules.functional.bulk_transfer.sheet_lifecycle import outgoing_records
            job.result={**job.result,'deleted':len(removed),'exported':len(job.payload['sheets']['connector']['append']),'sheet_records':outgoing_records(db,job.payload['sheets'])}
        return response(job)


def cleanup(db, config, uploads, owner):
    storage = ResourceStorage(config)
    for value in set(uploads):
        row = db.get(ResourceUpload, UUID(value))
        if row and row.owner_auth_subject == owner and row.resource_id is None and row.kit_id is None:
            # Also retain blobs referenced directly or by historical/shared catalogue rows.
            shared = db.scalar(select(Resource.id).where(Resource.storage_key == row.storage_key).limit(1))
            shared_kit = db.scalar(select(ActivityKit.id).where(ActivityKit.image_keys.contains([row.storage_key])).limit(1))
            if not shared and not shared_kit:
                storage.delete(row.storage_key); db.delete(row)


@router.post("/imports/{job_id}/cancel")
def cancel(request: Request, principal: Admin, job_id: UUID):
    with request.app.state.database.session() as db, db.begin():
        owner = principal_subject(db, principal); job = locked_job(db, job_id, owner)
        if job.status == "completed": fail(409, "A completed import cannot be cancelled; existing catalogue entries are retained.")
        cleanup(db, request.app.state.settings, job.payload.get("uploads", {}).values(), owner)
        job.status = "cancelled"
        return response(job)


def export_data(db, kind):
    query = select(MODELS[kind])
    if kind == "resources": query = query.where(MODELS[kind].deleted_at.is_(None), MODELS[kind].type.in_(["image", "video", "interactive"]))
    if kind == "students": query = query.where(~StudentProfile.auth_subject.in_(select(AdminRole.auth_subject)))
    rows = db.scalars(query.order_by(MODELS[kind].id).limit(5001)).all()
    if len(rows) > 5000: fail(413, "Export is limited to 5,000 records; use smaller catalogue batches.")
    records, mappings, media = [], [], {}
    for row in rows:
        data = snapshot(db, kind, row)
        identity = db.scalar(select(BulkIdentity).where(BulkIdentity.kind == kind, BulkIdentity.entity_id == row.id).order_by(BulkIdentity.record_key))
        key = identity.record_key if identity else str(row.id)
        record = {**data, "record_key": key, "existing_id": str(row.id)}
        education = data.get("learning_metadata", {})
        if kind == "resources": record["topic"] = education.get("topic_labels", [])
        for field in EDUCATION: record[field] = education.get("languages" if field == "teaching_languages" else field)
        for field, value in list(record.items()):
            if isinstance(value, list) and all(isinstance(v, str) for v in value): record[field] = json.dumps(value, ensure_ascii=False)
        if kind == "resources" and row.storage_key:
            name = "assets/" + str(row.id) + Path(row.storage_key).suffix
            media[name] = row.storage_key; record["file"] = name
        if kind == "activity-kits":
            names = []
            for index, storage_key in enumerate(row.image_keys):
                name = f"assets/{row.id}-{index}" + Path(storage_key).suffix
                media[name] = storage_key; names.append(name)
            record["image_files"] = "|".join(names)
        for link in data.get("expertise" if kind == "teachers" else "paths", []): mappings.append({"record_key": key, **link})
        records.append(record)
    return records, mappings, media


def copy_media(config, key):
    storage = ResourceStorage(config); key = storage.checked_key(key)
    if config.resource_storage_backend == "local":
        path = storage.local_path(key)
        if not path.is_file(): fail(422, "Export media is missing. Existing catalogue data was not changed.")
        if path.stat().st_size > 100 * 1024 * 1024: fail(413, "Export file exceeds the supported limit.")
        return path.read_bytes()
    secret = config.supabase_secret_key or config.supabase_service_role_key
    if not secret: fail(503, "Private media storage is not configured.")
    try:
        with httpx.stream("GET", config.supabase_url + "/storage/v1/object/" + config.resource_storage_bucket + "/" + key,
            headers={"apikey": secret.get_secret_value(), "Authorization": "Bearer " + secret.get_secret_value()}, timeout=120, follow_redirects=False) as upstream:
            if upstream.status_code != 200: fail(503, "Private media could not be exported. Retry later.")
            chunks, size = [], 0
            for chunk in upstream.iter_bytes():
                size += len(chunk)
                if size > 100 * 1024 * 1024: fail(413, "Export file exceeds the supported limit.")
                chunks.append(chunk)
            return b"".join(chunks)
    except httpx.HTTPError: fail(503, "Private media could not be exported. Retry later.")


@router.get("/{kind}/export")
def export(request: Request, principal: Admin, kind: Kind, package: bool = False):
    config = request.app.state.settings
    with request.app.state.database.session() as db:
        records, mappings, media = export_data(db, kind)
        paths = [p for c in db.scalars(select(Curriculum).where(Curriculum.state != "archived")) for p in path_choices(db, c.id)] if kind != "students" else []
        content = workbook(kind, records, mappings, paths)
    mime, suffix = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"
    if package:
        out = BytesIO(); expanded = len(content)
        if len(media) > 200: fail(413, "Package export is limited to 200 media files.")
        with ZipFile(out, "w", ZIP_DEFLATED) as archive:
            archive.writestr(kind + ".xlsx", content)
            for name, key in media.items():
                data = copy_media(config, key); expanded += len(data)
                if expanded > 200 * 1024 * 1024: fail(413, "Export package exceeds 200 MiB expanded.")
                archive.writestr(name, data)
        content = out.getvalue(); mime, suffix = "application/zip", ".zip"
        if len(content) > MAX_PACKAGE: fail(413, "Export package exceeds 120 MiB. Export the workbook instead.")
    return Response(content, media_type=mime, headers={"Content-Disposition": f'attachment; filename="{kind}{suffix}"', "Cache-Control": "private, no-store"})


@router.get("/{kind}/template")
def template(request: Request, principal: Admin, kind: Kind):
    with request.app.state.database.session() as db:
        paths = [p for c in db.scalars(select(Curriculum).where(Curriculum.state != "archived")) for p in path_choices(db, c.id)] if kind != "students" else []
        content = workbook(kind, paths=paths, template=True)
    return Response(content, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers={"Content-Disposition": f'attachment; filename="{kind}-template.xlsx"', "Cache-Control": "private, no-store"})
