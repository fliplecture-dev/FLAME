"""Transactional path-row editing over the normalized curriculum hierarchy."""
from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select

from app.modules.curriculum.catalogue import nodes, validate_publishable
from app.modules.curriculum.models import Category, CurriculumRevision, Domain, Level, Subject, Subtopic, Topic
from app.modules.curriculum.workbook_parser import match_key


def row_failure(code: str, key: str, field: str | None = None, status: int = 422):
    raise HTTPException(status, {"code": code, "row_key": key, "field": field})


def apply_path_batch(session, curriculum, changes: list[dict], *, record_revision: bool = True,
                     restore_archived: bool = False) -> dict:
    groups = nodes(session, curriculum.id, include_archived=True)
    known_subtopics = {item.id: item for item in groups[-1]}
    active_subtopic_ids = {item.id for item in groups[-1] if not item.archived}
    parent_fields = {Level: "curriculum_id", Subject: "level_id", Domain: "subject_id",
                     Category: "domain_id", Topic: "domain_id", Subtopic: "topic_id"}
    cached = {cls: {} for cls in parent_fields}
    for cls, group in zip(parent_fields, groups):
        for item in group:
            key = (getattr(item, parent_fields[cls]), item.normalized_name)
            if cls is Topic:
                key += (item.category_id,)
            cached[cls][key] = item
    seen_sources = set()
    seen_paths = set()
    for change in changes:
        key = change["key"]
        source_id = change.get("source_subtopic_id")
        if source_id is not None:
            if source_id in seen_sources:
                row_failure("duplicate_source_row", key)
            seen_sources.add(source_id)
            if source_id not in known_subtopics or known_subtopics[source_id].archived:
                row_failure("source_path_changed", key, status=409)
        if change["action"] == "delete":
            if source_id is None:
                row_failure("source_required", key)
            continue
        values = change.get("values")
        if not values:
            row_failure("values_required", key)
        path = tuple(match_key(values.get(field)) for field in
                     ("level", "subject", "domain", "category", "topic", "subtopic"))
        if path in seen_paths:
            row_failure("duplicate_row", key, "subtopic")
        seen_paths.add(path)

    created = changed = removed = 0
    changed_topics = set()
    results = []

    def get_or_create(cls, parent_field: str, parent_id, name: str, key: str,
                      field: str, **extra):
        nonlocal created
        normalized = match_key(name)
        lookup_key = (parent_id, normalized)
        if cls is Topic:
            lookup_key += (extra.get("category_id"),)
        node = cached[cls].get(lookup_key)
        if node is not None:
            if node.archived:
                if not restore_archived:
                    row_failure("archived_path_conflict", key, field, 409)
                # Explicit publication may bring a reviewed draft path back.
                # Reuse its identity so learning/resource links remain intact.
                node.archived = False
                node.version += 1
            return node
        attrs = {"id": uuid4(), "name": name, "normalized_name": normalized,
                 parent_field: parent_id, **extra}
        if cls is Level:
            attrs.update(code=name, normalized_code=normalized)
        node = cls(**attrs)
        session.add(node)
        cached[cls][lookup_key] = node
        created += 1
        return node

    upserts = [change for change in changes if change["action"] != "delete"]
    resolved = {id(change): {} for change in upserts}
    for change in upserts:
        values = change["values"]
        resolved[id(change)]["level"] = get_or_create(
            Level, "curriculum_id", curriculum.id, values["level"], change["key"], "level")
    session.flush()
    for change in upserts:
        values = change["values"]
        path = resolved[id(change)]
        path["subject"] = get_or_create(
            Subject, "level_id", path["level"].id, values["subject"], change["key"], "subject")
    session.flush()
    for change in upserts:
        values = change["values"]
        path = resolved[id(change)]
        path["domain"] = get_or_create(
            Domain, "subject_id", path["subject"].id, values["domain"], change["key"], "domain")
    session.flush()
    for change in upserts:
        values = change["values"]
        path = resolved[id(change)]
        path["category"] = (get_or_create(Category, "domain_id", path["domain"].id,
            values["category"], change["key"], "category") if values.get("category") else None)
    session.flush()
    for change in upserts:
        values = change["values"]
        path = resolved[id(change)]
        path["topic"] = get_or_create(Topic, "domain_id", path["domain"].id,
            values["topic"], change["key"], "topic",
            category_id=path["category"].id if path["category"] else None)
    session.flush()
    for change in upserts:
        values = change["values"]
        path = resolved[id(change)]
        path["subtopic"] = get_or_create(
            Subtopic, "topic_id", path["topic"].id, values["subtopic"], change["key"], "subtopic")
    session.flush()

    for change in changes:
        key = change["key"]
        source_id = change.get("source_subtopic_id")
        source = known_subtopics.get(source_id) if source_id else None
        if change["action"] == "delete":
            source.archived = True
            source.version += 1
            changed_topics.add(source.topic_id)
            removed += 1
            results.append({"key": key, "status": "removed"})
            continue
        target = resolved[id(change)]["subtopic"]
        if target.id != source_id and target.id in active_subtopic_ids:
            row_failure("duplicate_existing_path", key, "subtopic")
        if source is not None and source.id != target.id:
            source.archived = True
            source.version += 1
            changed_topics.add(source.topic_id)
        if source is None or source.id != target.id:
            changed += 1
        results.append({"key": key, "status": "saved", "subtopic_id": str(target.id)})
    session.flush()
    for topic_id in changed_topics:
        active = session.scalar(select(func.count()).select_from(Subtopic).where(
            Subtopic.topic_id == topic_id, Subtopic.archived.is_(False)))
        if not active:
            topic = session.get(Topic, topic_id)
            topic.archived = True
            topic.version += 1
    session.flush()
    if curriculum.state == "published":
        validate_publishable(session, curriculum)
    if record_revision and (created or changed or removed):
        curriculum.revision += 1
        session.add(CurriculumRevision(
            curriculum_id=curriculum.id, number=curriculum.revision,
            change_kind="edit_paths",
            details={"rows": len(changes), "created_nodes": created,
                     "changed_paths": changed, "removed_paths": removed}))
    return {"revision": curriculum.revision, "created_nodes": created,
            "changed_paths": changed, "removed_paths": removed, "rows": results}




