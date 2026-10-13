"""Private curriculum draft snapshots and atomic publication."""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from app.modules.curriculum.catalogue import nodes, validate_publishable
from app.modules.curriculum.models import (
    Category, CurriculumDraft, CurriculumRevision, Domain, Level, Subject, Subtopic, Topic,
)
from app.modules.curriculum.path_batch import apply_path_batch
from app.modules.curriculum.workbook_parser import match_key

FIELDS = ("level", "subject", "domain", "category", "topic", "subtopic")
REQUIRED = ("level", "subject", "domain", "topic", "subtopic")


def _fail(status: int, code: str, key: str | None = None, field: str | None = None):
    detail = {"code": code}
    if key is not None:
        detail["row_key"] = key
    if field is not None:
        detail["field"] = field
    raise HTTPException(status, detail)


def published_paths(session, curriculum_id: UUID) -> list[dict]:
    levels, subjects, domains, categories, topics, subtopics = nodes(
        session, curriculum_id, include_archived=False)
    level_map = {item.id: item for item in levels}
    subject_map = {item.id: item for item in subjects}
    domain_map = {item.id: item for item in domains}
    category_map = {item.id: item for item in categories}
    topic_map = {item.id: item for item in topics}
    result = []
    for subtopic in subtopics:
        topic = topic_map[subtopic.topic_id]
        domain = domain_map[topic.domain_id]
        subject = subject_map[domain.subject_id]
        level = level_map[subject.level_id]
        category = category_map.get(topic.category_id)
        result.append({
            "key": str(subtopic.id),
            "ids": {
                "level": str(level.id), "subject": str(subject.id), "domain": str(domain.id),
                "category": str(category.id) if category else None,
                "topic": str(topic.id), "subtopic": str(subtopic.id),
            },
            "values": {
                "level": level.name, "subject": subject.name, "domain": domain.name,
                "category": category.name if category else "", "topic": topic.name,
                "subtopic": subtopic.name,
            },
        })
    return sorted(result, key=lambda row: tuple(
        match_key(row["values"][field]) or "" for field in FIELDS))


def _normalize_values(values: dict, key: str) -> dict:
    result = {}
    for field in FIELDS:
        value = str(values.get(field) or "").strip()
        if field in REQUIRED and not value:
            _fail(422, "required", key, field)
        limit = 80 if field == "level" else 255
        if len(value) > limit:
            _fail(422, "value_too_long", key, field)
        result[field] = value
    return result


def _path_key(values: dict) -> tuple:
    return tuple(match_key(values[field]) for field in FIELDS)


def _assign_ids(paths: list[dict]) -> list[dict]:
    """Reuse stable IDs by logical prefix and allocate IDs only for new nodes."""
    indexes = {field: {} for field in FIELDS}
    for source in paths:
        prefix = []
        for field in FIELDS:
            prefix.append(match_key(source["values"][field]))
            candidate = (source.get("ids") or {}).get(field)
            if candidate:
                indexes[field].setdefault(tuple(prefix), candidate)
    result = []
    for source in paths:
        row = deepcopy(source)
        values = row["values"]
        supplied = row.get("ids") or {}
        ids = {}
        prefix = []
        for field in FIELDS:
            value = values[field]
            if field == "category" and not value:
                ids[field] = None
                prefix.append(None)
                continue
            prefix.append(match_key(value))
            logical = tuple(prefix)
            candidate = supplied.get(field)
            existing = indexes[field].get(logical)
            ids[field] = existing or candidate or str(uuid4())
            indexes[field][logical] = ids[field]
        row["ids"] = ids
        row["key"] = row.get("key") or ids["subtopic"]
        result.append(row)
    return result


def published_revision(session, curriculum) -> int:
    """Metadata revisions do not create a new immutable member publication."""
    return int(session.scalar(select(func.max(CurriculumRevision.number)).where(
        CurriculumRevision.curriculum_id == curriculum.id,
        CurriculumRevision.change_kind == "publish")) or 0)


def rebase_state_only_draft(session, curriculum, draft: CurriculumDraft) -> None:
    """Rebase only over recorded changes that cannot alter hierarchy paths."""
    if draft.base_revision == curriculum.revision:
        return
    changes = session.scalars(select(CurriculumRevision.change_kind).where(
        CurriculumRevision.curriculum_id == curriculum.id,
        CurriculumRevision.number > draft.base_revision,
        CurriculumRevision.number <= curriculum.revision,
    ).order_by(CurriculumRevision.number)).all()
    if len(changes) == curriculum.revision - draft.base_revision and all(
            change in {"archive_curriculum", "restore", "edit_curriculum"} for change in changes):
        draft.base_revision = curriculum.revision


def get_or_create_draft(session, curriculum, owner: str | None = None,
                        *, lock: bool = False) -> CurriculumDraft:
    query = select(CurriculumDraft).where(
        CurriculumDraft.curriculum_id == curriculum.id)
    if lock:
        query = query.with_for_update()
    draft = session.scalar(query)
    if draft is None:
        draft = CurriculumDraft(
            curriculum_id=curriculum.id,
            base_revision=curriculum.revision,
            revision=1,
            paths=published_paths(session, curriculum.id),
            updated_by_subject=owner,
        )
        session.add(draft)
        session.flush()
    else:
        rebase_state_only_draft(session, curriculum, draft)
    return draft


def draft_summary(session, curriculum) -> dict:
    draft = session.get(CurriculumDraft, curriculum.id)
    published = published_paths(session, curriculum.id)
    current = draft.paths if draft else published
    old = {_path_key(row["values"]): row for row in published}
    new = {_path_key(row["values"]): row for row in current}
    return {
        "has_draft": draft is not None,
        "published_revision": published_revision(session, curriculum),
        "draft_revision": draft.revision if draft else 0,
        "base_revision": draft.base_revision if draft else curriculum.revision,
        "counts": {
            "added": len(new.keys() - old.keys()),
            "removed": len(old.keys() - new.keys()),
            "unchanged": len(old.keys() & new.keys()),
            "total": len(new),
        },
        "conflicts": 1 if draft and draft.base_revision != curriculum.revision else 0,
    }


def save_draft_changes(session, curriculum, expected_revision: int,
                       changes: list[dict], owner: str | None = None) -> dict:
    draft = get_or_create_draft(session, curriculum, owner, lock=True)
    if draft.revision != expected_revision:
        _fail(409, "updated_elsewhere")
    paths = deepcopy(draft.paths)
    by_subtopic = {
        row.get("ids", {}).get("subtopic"): index
        for index, row in enumerate(paths)
        if row.get("ids", {}).get("subtopic")
    }
    removed = set()
    for change in changes:
        key = change["key"]
        source = str(change.get("source_subtopic_id") or "") or None
        index = by_subtopic.get(source) if source else None
        if change["action"] == "delete":
            if index is None:
                _fail(409, "updated_elsewhere", key)
            removed.add(index)
            continue
        values = _normalize_values(change.get("values") or {}, key)
        row = {"key": key, "values": values, "ids": {}}
        if index is not None:
            row["ids"] = deepcopy(paths[index].get("ids") or {})
            # Moving one path cannot reuse a shared ancestor ID under another logical prefix.
            first_changed = next((position for position, field in enumerate(FIELDS)
                if match_key(values[field]) != match_key(paths[index]["values"][field])), len(FIELDS))
            for field in FIELDS[first_changed:-1]:
                row["ids"].pop(field, None)
            row["key"] = paths[index].get("key") or key
            paths[index] = row
        else:
            paths.append(row)
    paths = [row for index, row in enumerate(paths) if index not in removed]
    seen = {}
    for row in paths:
        normalized = _path_key(row["values"])
        if normalized in seen:
            _fail(422, "duplicate_row", row["key"], "subtopic")
        seen[normalized] = row["key"]
    draft.paths = _assign_ids(paths)
    draft.revision += 1
    draft.updated_by_subject = owner
    saved_by_key = {row["key"]: row for row in draft.paths}
    return {
        "draft_revision": draft.revision,
        "published_revision": published_revision(session, curriculum),
        "base_revision": draft.base_revision,
        "rows": [{
            "key": change["key"],
            "status": "draft_saved",
            "subtopic_id": (
                saved_by_key.get(change["key"], {}).get("ids", {}).get("subtopic")
                if change["action"] == "upsert" else None
            ),
        } for change in changes],
        "counts": draft_summary(session, curriculum)["counts"],
    }


def rename_draft_node(session, curriculum, expected_revision: int, field: str,
                      node_id: UUID, name: str, owner: str | None = None) -> dict:
    if field not in FIELDS or field == "category" and not name.strip():
        _fail(422, "invalid_rename")
    draft = get_or_create_draft(session, curriculum, owner, lock=True)
    if draft.revision != expected_revision:
        _fail(409, "updated_elsewhere")
    changed = 0
    paths = deepcopy(draft.paths)
    for row in paths:
        if row.get("ids", {}).get(field) == str(node_id):
            row["values"][field] = name.strip()
            changed += 1
    if not changed:
        _fail(409, "updated_elsewhere")
    seen = set()
    for row in paths:
        key = _path_key(row["values"])
        if key in seen:
            _fail(422, "duplicate_row")
        seen.add(key)
    draft.paths = _assign_ids(paths)
    draft.revision += 1
    draft.updated_by_subject = owner
    return {"draft_revision": draft.revision, "affected_paths": changed}


def replace_draft(session, curriculum, rows: list[dict], owner: str | None,
                  source_import_id: UUID | None = None) -> CurriculumDraft:
    draft = get_or_create_draft(session, curriculum, owner, lock=True)
    if draft.base_revision != curriculum.revision:
        # A confirmed full replacement is rebased on the latest published revision.
        draft.base_revision = curriculum.revision
        draft.paths = published_paths(session, curriculum.id)
    existing_by_key = {_path_key(row["values"]): row for row in draft.paths}
    prefixes = {}
    for old in draft.paths:
        logical = _path_key(old["values"])
        for position, field in enumerate(FIELDS):
            if old.get("ids", {}).get(field):
                prefixes[(field, logical[:position + 1])] = old["ids"][field]
    paths = []
    for index, values in enumerate(rows):
        clean = _normalize_values(values, "import:" + str(index + 1))
        prior = existing_by_key.get(_path_key(clean))
        paths.append({
            "key": prior.get("key") if prior else str(uuid4()),
            "ids": deepcopy(prior.get("ids") or {}) if prior else {
                field: prefixes.get((field, _path_key(clean)[:position + 1]))
                for position, field in enumerate(FIELDS)},
            "values": clean,
        })
    if len({_path_key(row["values"]) for row in paths}) != len(paths):
        _fail(422, "duplicate_row")
    draft.paths = _assign_ids(paths)
    draft.revision += 1
    draft.source_import_id = source_import_id
    draft.updated_by_subject = owner
    return draft


def draft_tree(session, curriculum) -> dict:
    draft = get_or_create_draft(session, curriculum)
    published = {_path_key(row["values"]): row for row in published_paths(session, curriculum.id)}
    root = {
        "id": str(curriculum.id), "code": curriculum.code, "name": curriculum.name,
        "description": curriculum.description, "state": curriculum.state,
        "version": curriculum.version, "revision": curriculum.revision,
        "published_revision": published_revision(session, curriculum),
        "draft_revision": draft.revision, "base_revision": draft.base_revision,
        "has_draft": True, "levels": [],
    }
    collections = {
        "level": "levels", "subject": "subjects", "domain": "domains",
        "category": "categories", "topic": "topics", "subtopic": "subtopics",
    }
    lookup: dict[tuple[str, str], dict] = {}
    for row in draft.paths:
        parent = root
        for field in FIELDS:
            value = row["values"][field]
            if field == "category" and not value:
                continue
            node_id = row["ids"][field]
            lookup_key = (field, node_id)
            node = lookup.get(lookup_key)
            if node is None:
                node = {"id": node_id, "name": value, "version": draft.revision,
                        "archived": False, collections.get({
                            "level": "subject", "subject": "domain", "domain": "category",
                            "category": "topic", "topic": "subtopic",
                        }.get(field, ""), ""): []}
                # Remove the synthetic empty collection on terminal nodes.
                node.pop("", None)
                parent.setdefault(collections[field], []).append(node)
                lookup[lookup_key] = node
            parent = node
        status = "unchanged" if _path_key(row["values"]) in published else "draft_change"
        parent["draft_status"] = status
    for container in [root, *lookup.values()]:
        for name in collections.values():
            if name in container:
                container[name].sort(key=lambda item: (item["name"].casefold(), item["id"]))
    return root


def publish_draft(session, curriculum, expected_version: int,
                  expected_draft_revision: int) -> dict:
    if curriculum.version != expected_version:
        _fail(409, "updated_elsewhere")
    draft = session.scalar(select(CurriculumDraft).where(
        CurriculumDraft.curriculum_id == curriculum.id).with_for_update())
    if draft is None:
        validate_publishable(session, curriculum)
    else:
        rebase_state_only_draft(session, curriculum, draft)
        if draft.revision != expected_draft_revision or draft.base_revision != curriculum.revision:
            _fail(409, "updated_elsewhere")
        current = published_paths(session, curriculum.id)
        current_ids = {row["ids"]["subtopic"] for row in current}
        wanted_ids = {row["ids"]["subtopic"] for row in draft.paths}
        changes = []
        for row in draft.paths:
            source = row["ids"]["subtopic"] if row["ids"]["subtopic"] in current_ids else None
            current_row = next((item for item in current if item["ids"]["subtopic"] == source), None)
            if current_row is None or _path_key(current_row["values"]) != _path_key(row["values"]):
                changes.append({
                    "key": row["key"], "action": "upsert",
                    "source_subtopic_id": UUID(source) if source else None,
                    "values": row["values"],
                })
        for row in current:
            if row["ids"]["subtopic"] not in wanted_ids:
                changes.append({
                    "key": row["key"], "action": "delete",
                    "source_subtopic_id": UUID(row["ids"]["subtopic"]), "values": None,
                })
        summary = draft_summary(session, curriculum)
        if changes:
            apply_path_batch(session, curriculum, changes, record_revision=False,
                             restore_archived=True)
        validate_publishable(session, curriculum)
    before_state = curriculum.state
    curriculum.state = "published"
    curriculum.version += 1
    curriculum.revision += 1
    snapshot = published_paths(session, curriculum.id)
    if draft is None:
        summary = {
            "counts": {"added": len(snapshot), "removed": 0, "unchanged": 0, "total": len(snapshot)}}
    session.add(CurriculumRevision(
        curriculum_id=curriculum.id, number=curriculum.revision,
        change_kind="publish",
        details={"before_state": before_state, "after_state": "published",
                 "snapshot": snapshot, "counts": summary["counts"]},
    ))
    if draft is not None:
        session.delete(draft)
    return {
        "id": str(curriculum.id), "state": curriculum.state,
        "version": curriculum.version, "revision": curriculum.revision,
        "published_revision": curriculum.revision, "draft_revision": 0,
    }



