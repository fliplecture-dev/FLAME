"""Additive transfer using catalogue schemas, path/media validators and versioned previews."""
from app.modules.functional.bulk_transfer.workbooks import assign_record_keys
import hashlib
import json
import re
from uuid import UUID, uuid4
from sqlalchemy import select, func
from pydantic import BaseModel, ConfigDict, Field, field_validator
from fastapi import HTTPException
from app.contracts.learning_metadata import LearningMetadata, metadata_data
from app.modules.functional.bulk_transfer.models import BulkIdentity
from app.modules.functional.bulk_transfer.workbooks import EDUCATION
from app.modules.functional.resources.models import Resource, ResourceTopic, ResourceUpload
from app.modules.functional.resources.router import DraftCreate, ResourcePath
from app.modules.functional.resources.service import validate_resource_paths, admin_data, path_info
from app.modules.functional.resources.validation import validate_external_url, MEDIA_TYPES
from app.modules.functional.resources.external_video import inspect_video, is_provider_url
from app.modules.functional.teachers.models import Teacher, TeacherExpertise
from app.modules.functional.teachers.router import TeacherDraft, ExpertiseInput, expertise_valid, teacher_data, publication_check as teacher_check
from app.modules.functional.activity_kits.models import ActivityKit, KitTopic
from app.modules.functional.activity_kits.router import KitDraft, supplier, kit_data
from app.modules.functional.activity_kits.service import publication_check as kit_check
from app.modules.functional.identity.models import StudentProfile, AdminRole
from app.modules.functional.bulk_transfer.errors import fail

MODELS = {"resources": Resource, "teachers": Teacher, "students": StudentProfile, "activity-kits": ActivityKit}


class StudentDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    display_name: str | None = Field(default=None, max_length=255)
    email: str | None = Field(default=None, min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def email_format(cls, value):
        if value is None: return None
        value = value.strip().lower()
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
            raise ValueError("Enter a valid email address.")
        return value


def split(value):
    if isinstance(value, str) and value.strip().startswith("["):
        parsed = json.loads(value)
        if not isinstance(parsed, list) or any(not isinstance(v, str) for v in parsed): raise ValueError("List cells must contain strings.")
        return parsed
    return [s.strip() for s in str(value or "").replace("\n", "|").split("|") if s.strip()]


def digest(value):
    def stable(item):
        if isinstance(item, dict): return {k: stable(v) for k, v in item.items() if k != "verified_at"}
        if isinstance(item, list): return [stable(v) for v in item]
        return item
    # Provider inspection is repeated at commit. Its fresh check timestamp is not an edit;
    # source identity, returned metadata, catalogue versions and saved values still participate.
    return hashlib.sha256(json.dumps(stable(value), sort_keys=True, default=str).encode()).hexdigest()


def raw_body(kind, record, mappings, uploads):
    if kind == "resources":
        problems=[]
        if record.get("rights_basis") not in (None,"","owned","licensed","permission"):
            problems.append("rights_basis: use owned, licensed or permission only when verified; leave blank for an unreviewed draft. unknown is not accepted.")
        unsupported=[value for value in split(record.get("purposes")) if value not in {"explain","demonstrate","practise","human_help"}]
        if unsupported:problems.append("purposes: unsupported values "+", ".join(unsupported)+". Use explain, demonstrate, practise or human_help, or leave this optional cell blank.")
        if record.get("type")!="interactive" and not record.get("file") and not record.get("external_url"):
            problems.append("Media source: provide a supported external_url, or file=assets/name.html (or another supported media file) and include that file in the ZIP.")
        if problems:fail(422," ".join(problems))
    body = {k: v for k, v in record.items() if k not in {"record_key", "existing_id", "file", "image_files", "topic", "_row", "published", "version", "status", *EDUCATION} and v != ""}
    if kind == "students":
        return StudentDraft.model_validate(body).model_dump(mode="json")
    education = {k: record[k] for k in EDUCATION if record.get(k) not in (None, "")}
    for key in ("concepts", "synonyms", "purposes"):
        if key in education:
            education[key] = split(education[key])
    if kind == "resources": education["topic_labels"] = split(record.get("topic"))
    education["languages"] = split(education.pop("teaching_languages", None))
    body["learning_metadata"] = LearningMetadata.model_validate(education).model_dump(mode="json")
    links = [m for m in mappings if str(m.get("record_key", "")).strip() == record["record_key"]]
    links = list({(str(m.get("subject_id") or "") if kind == "teachers" else "", str(m.get("topic_id") or ""), str(m.get("subtopic_id") or "")): m for m in links}.values())
    if kind == "teachers":
        if any(m.get("subtopic_id") for m in links): fail(422, "Teachers support subject/topic expertise, not subtopic mappings.")
        body["languages"] = split(body.get("languages"))
        body["expertise"] = [{"subject_id": m.get("subject_id"), "topic_id": m.get("topic_id") or None, "claim_status": "declared"} for m in links]
        return TeacherDraft.model_validate(body).model_dump(mode="json")
    body["paths"] = [{"topic_id": m.get("topic_id"), "subtopic_id": m.get("subtopic_id") or None} for m in links]
    if kind == "resources":
        if record.get("file"):
            body["upload_id"] = uploads.get(record["record_key"] + "::" + str(record["file"]), str(UUID(int=1)))
        return DraftCreate.model_validate(body).model_dump(mode="json", exclude={"thumbnail_upload_id"})
    body["materials"] = split(body.get("materials"))
    body["image_upload_ids"] = [uploads.get(record["record_key"] + "::" + f, str(UUID(int=i+1))) for i, f in enumerate(split(record.get("image_files")))]
    return KitDraft.model_validate(body).model_dump(mode="json")


def identity_match(db, kind, record, body):
    model = MODELS[kind]
    saved = db.scalar(select(BulkIdentity).where(BulkIdentity.kind == kind, BulkIdentity.record_key == record["record_key"]))
    if record.get("existing_id"):
        row = db.get(model, UUID(str(record["existing_id"])))
        if row is None:
            fail(422, "existing_id was not found. Correct it, or clear it for a new item.")
        if saved and saved.entity_id != row.id:
            fail(422, "record_key and existing_id identify different items.")
        return row
    if saved:
        row = db.get(model, saved.entity_id)
        if row is None:
            fail(422, "This record_key refers to a removed item. Use a new key.")
        return row
    if kind == "students":
        if not body.get("email"): fail(422, "New students require an email. Use an existing_id or registered key to merge an existing profile without one.")
        query = select(model).where(func.lower(model.email) == body["email"])
    elif kind == "resources" and body.get("external_url"):
        query = select(model).where(model.external_url == body["external_url"])
    else:
        name = "title" if kind == "resources" else "name"
        query = select(model).where(func.lower(func.trim(getattr(model, name))) == body[name].strip().lower())
    if kind == "resources":
        query = query.where(model.deleted_at.is_(None), model.type == body["type"])
    matches = db.scalars(query).all()
    if len(matches) > 1:
        fail(422, "Multiple existing items match. Enter the exact existing_id from an export.")
    return matches[0] if matches else None


def snapshot(db, kind, row):
    if kind == "resources": return admin_data(db, row)
    if kind == "teachers": return teacher_data(db, row)
    if kind == "activity-kits": return kit_data(db, row)
    return {"id": str(row.id), "email": row.email, "display_name": row.display_name, "status": row.status}


def changes(kind, before, body):
    updates, preserved = {}, []
    published_media = kind == "resources" and before.get("published")
    excluded = {"paths", "expertise", "upload_id", "image_upload_ids", "creation_id", "external_url", "type", "availability"}
    if kind == "students": excluded |= {"email"}
    for key, value in body.items():
        if key in excluded or value in (None, "", [], {}):
            continue
        current = before.get(key)
        if published_media:
            if current != value: preserved.append(key)
        elif key == "learning_metadata":
            merged = metadata_data(current)
            for field, incoming in value.items():
                if field in {"grade_min", "grade_max"}:
                    continue
                if isinstance(incoming, list): merged[field] = list(dict.fromkeys(merged[field] + incoming))
            if merged["grade_min"] is None and value.get("grade_min") is not None:
                merged["grade_min"], merged["grade_max"] = value["grade_min"], value["grade_max"]
            merged = LearningMetadata.model_validate(merged).model_dump(mode="json")
            if merged != metadata_data(current): updates[key] = merged
        elif isinstance(value, list):
            merged = list(dict.fromkeys((current or []) + value))
            limit = 20 if kind == "teachers" and key == "languages" else 100 if kind == "activity-kits" and key == "materials" else None
            if limit and len(merged) > limit: raise ValueError(f"Merged {key} exceeds {limit} entries; existing values were preserved.")
            if merged != current: updates[key] = merged
        elif current in (None, ""):
            updates[key] = value
        elif current != value:
            preserved.append(key)
    # Cost/currency must remain a pair; preserve both if either already exists.
    if kind == "activity-kits" and (before.get("cost") is not None or before.get("currency")):
        updates.pop("cost", None); updates.pop("currency", None)
    return updates, preserved


def plan(db, config, kind, payload):
    entries, keys, batch, by_key = [], set(), {}, {}
    records, mappings = payload["records"], payload["mappings"]
    assign_record_keys(kind, records)
    if not records: fail(422, "Records has no data rows. Add at least one item.")
    known_keys = {str(r.get("record_key", "")).strip() for r in records}
    orphan = [m for m in mappings if str(m.get("record_key", "")).strip() not in known_keys]
    if orphan:
        fail(422, "Mappings refers to a record_key absent from Records. For a partial workbook, keep only Mappings rows matching the included Records. Already saved mappings are preserved.")
    for original in records:
        record = dict(original)
        key = str(record.get("record_key", "")).strip()
        entry = {"row": record["_row"], "record_key": key, "name": str(record.get("title") or record.get("name") or record.get("display_name") or record.get("email") or key), "errors": []}
        entries.append(entry)
        try:
            if not key or len(key) > 255 or any(ord(c) < 32 for c in key): fail(422, "Enter a stable record_key (maximum 255 characters).")
            keys.add(key); record["record_key"] = key
            # A metadata-only merge can reuse retained media by ID or registered key.
            retained_source = False
            if kind == "resources" and not record.get("file"):
                existing = None
                if record.get("existing_id"):
                    existing = db.get(Resource, UUID(str(record["existing_id"])))
                else:
                    registered = db.scalar(select(BulkIdentity).where(BulkIdentity.kind == kind, BulkIdentity.record_key == key))
                    if registered: existing = db.get(Resource, registered.entity_id)
                if existing and (not record.get('external_url') or
                                 (record.get('external_url') == existing.external_url and
                                  (not record.get('type') or record.get('type') == existing.type))):
                    record["type"] = record.get("type") or existing.type
                    record["title"] = record.get("title") or existing.title
                    record["external_url"] = existing.external_url or (None if existing.type=="interactive" and not existing.storage_key else "https://placeholder.invalid/stored")
                    retained_source = True
            body = raw_body(kind, record, mappings, payload.get("uploads", {}))
            if kind == "resources" and body.get("external_url") and not retained_source:
                if body["type"] == "video" and is_provider_url(body["external_url"]):
                    body["external_video"] = inspect_video(body["external_url"], config)
                    body["external_url"] = body["external_video"]["canonical_url"]
                else:
                    if is_provider_url(body["external_url"]): fail(422, "Choose External video for a provider URL.")
                    body["external_url"] = validate_external_url(body["external_url"], {h.strip().lower() for h in config.resource_allowed_hosts.split(",") if h.strip()})
            row = identity_match(db, kind, record, body)
            if isinstance(row, Resource) and row.deleted_at is not None: fail(422, "This resource has been deleted; it cannot be merged.")
            if kind == "students" and row and row.status not in ("active", "pending"): fail(422, "This student profile is inactive or removed. Bulk import cannot reactivate or change it.")
            if kind == "students" and row and db.get(AdminRole, row.auth_subject): fail(422, "This email belongs to an administrator, not a student.")
            natural = (body.get("external_url") if kind == "resources" else body.get("email") if kind == "students" else body.get("name", "").strip().casefold()) or body.get("title", "").casefold()
            natural = (body.get("type", kind), str(row.id) if row else natural)
            key_alias = by_key.get(key)
            if key_alias:
                prior_id = key_alias["effective"].get("id")
                if row is not None and str(row.id) != prior_id:
                    fail(422, "The repeated record_key identifies different existing items. Correct the key or existing_id.")
                if prior_id and row is None:
                    row = db.get(MODELS[kind], UUID(prior_id))
            alias = key_alias or batch.get(natural)
            original_before = snapshot(db, kind, row) if row else {}
            before = alias["effective"] if alias else original_before
            updates, preserved = changes(kind, before, body) if before else ({}, [])
            if kind == "teachers":
                links = [ExpertiseInput.model_validate(x) for x in body["expertise"]]
                old = {(x["subject_id"], x.get("topic_id")) for x in before.get("expertise", [])}
                additions = [x for x in body["expertise"] if (x["subject_id"], x.get("topic_id")) not in old]
                for link in additions: expertise_valid(db, ExpertiseInput.model_validate(link), bool(before.get("published")))
            elif kind != "students":
                old = {(x["topic_id"], x.get("subtopic_id")) for x in before.get("paths", [])}
                additions = [x for x in body["paths"] if (x["topic_id"], x.get("subtopic_id")) not in old]
                validate_resource_paths(db, [ResourcePath.model_validate(x) for x in additions])
                if before.get("published"):
                    for x in additions: path_info(db, UUID(x["topic_id"]), UUID(x["subtopic_id"]) if x.get("subtopic_id") else None, published=True)
            else: additions = []
            files = ([str(record["file"])] if kind == "resources" and record.get("file") else split(record.get("image_files")))
            if not before and any(key + "::" + f not in payload.get("uploads", {}) for f in files):
                missing = [f for f in files if f not in payload.get("asset_names", [])]
                if missing: fail(422, "Missing bundled media: " + ", ".join(missing) + ". For new file-based media, upload a ZIP with resources.xlsx at the root and these files under assets/. Existing media is retained by its ID/key.")
            if not before and kind == "resources" and body.get("upload_id"):
                upload = db.get(ResourceUpload, UUID(body["upload_id"]))
                if upload and upload.media_type not in MEDIA_TYPES[body["type"]]: fail(422, "Resource media type does not match its bundled file.")
            if kind == "activity-kits": supplier(body.get("supplier_url"))
            operation = "merge" if before and (updates or additions) else "unchanged" if before else "add"
            entry.update(operation=operation, existing_id=str(row.id) if row else None, batch_key=alias["record_key"] if alias and row is None else None,
                version=before.get("version"), fingerprint=digest(original_before or before) if before else None, updates=updates, preserved_fields=preserved,
                mapping_additions=additions, body=body, files=files if not before else [])
            effective = {**before, **updates} if before else body
            if kind == "teachers": effective = {**effective, "expertise": before.get("expertise", []) + additions}
            elif kind != "students": effective = {**effective, "paths": before.get("paths", []) + additions}
            batch[natural] = {"record_key": key, "effective": effective}
            by_key[key] = batch[natural]
        except (ValueError, TypeError, HTTPException) as error:
            detail = error.detail if isinstance(error, HTTPException) else str(error)
            entry["errors"] = [str(detail)[:1800]]; entry["operation"] = "invalid"
    return {"entries": entries, "counts": {op: sum(e["operation"] == op for e in entries) for op in ("add", "merge", "unchanged", "invalid")}, "total": len(entries)}


def apply(db, config, kind, preview, owner):
    ids, result = {}, {"added": 0, "merged": 0, "unchanged": 0, "mappings_added": 0}
    for entry in preview["entries"]:
        body = dict(entry["body"])
        row_id = entry["existing_id"] or ids.get(entry.get("batch_key"))
        row = db.get(MODELS[kind], UUID(row_id)) if row_id else None
        if row is None:
            if kind == "resources":
                upload = db.get(ResourceUpload, UUID(body["upload_id"])) if body.get("upload_id") else None
                if upload and (upload.owner_auth_subject != owner or upload.resource_id or upload.kit_id): fail(409, "Staged media is no longer available. Review the comparison again.")
                if upload and upload.media_type not in MEDIA_TYPES[body["type"]]: fail(422, "Resource media type does not match the file.")
                fields = {k: v for k, v in body.items() if k not in {"paths", "upload_id", "creation_id"}}
                row = Resource(**fields, storage_key=upload.storage_key if upload else None, mime_type=upload.mime_type if upload else None, byte_size=upload.byte_size if upload else None)
            elif kind == "teachers": row = Teacher(**{k: v for k, v in body.items() if k != "expertise"})
            elif kind == "activity-kits":
                row = ActivityKit(**{k: v for k, v in body.items() if k not in {"paths", "image_upload_ids"}})
                row.supplier_url = supplier(row.supplier_url)
            else: row = StudentProfile(**body, auth_subject="bulk-pending:" + uuid4().hex, status="pending")
            db.add(row); db.flush(); result["added"] += 1
            if kind == "resources" and upload: upload.resource_id = row.id
            if kind == "activity-kits":
                from app.modules.functional.activity_kits.router import replace_images
                replace_images(db, row, [UUID(x) for x in body["image_upload_ids"]], owner)
        else:
            before = snapshot(db, kind, row)
            updates, _ = changes(kind, before, body)
            for field, value in updates.items(): setattr(row, field, value)
            result["merged" if entry["operation"] == "merge" else "unchanged"] += 1
        added = entry["mapping_additions"]
        if kind == "teachers":
            for link in added: db.add(TeacherExpertise(teacher_id=row.id, subject_id=UUID(link["subject_id"]), topic_id=UUID(link["topic_id"]) if link.get("topic_id") else None, claim_status="declared"))
        elif kind in {"resources", "activity-kits"}:
            for link in added:
                cls, field = (ResourceTopic, "resource_id") if kind == "resources" else (KitTopic, "kit_id")
                db.add(cls(**{field: row.id}, topic_id=UUID(link["topic_id"]), subtopic_id=UUID(link["subtopic_id"]) if link.get("subtopic_id") else None))
        if row_id and entry["operation"] == "merge" and hasattr(row, "version"): row.version += 1
        db.flush()
        if getattr(row, "published", False) and entry["operation"] == "merge":
            if kind == "teachers": teacher_check(db, row)
            elif kind == "activity-kits": kit_check(db, row, config)
        identity = db.scalar(select(BulkIdentity).where(BulkIdentity.kind == kind, BulkIdentity.record_key == entry["record_key"]))
        if identity is None: db.add(BulkIdentity(kind=kind, record_key=entry["record_key"], entity_id=row.id))
        ids[entry["record_key"]] = str(row.id); result["mappings_added"] += len(added)
    result["ids"] = ids
    return result
