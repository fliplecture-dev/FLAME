"""Member browsing over catalogue owners; never rank or store recommendations."""
import logging
from time import perf_counter
from app.core.domain_errors import fail
from app.contracts.catalogue import suitable_for as suitable
from app.modules.curriculum.public_paths import describe_browse_path
from app.modules.curriculum.public_paths import browse_search_paths
from app.modules.teaching.resolution import words, contains_phrase
from app.modules.resources.candidates import eligible_candidates as media_candidates
from app.modules.teachers.candidates import eligible_candidates as teacher_candidates
from app.modules.activity_kits.candidates import eligible_candidates as kit_candidates

LOGGER = logging.getLogger("flame.explore")


def curiosity_context(db, question):
    """Match explicit published names, collapse topic children, and expose ambiguity."""
    terms = words(question)
    if not terms:
        return {"context": None, "candidates": []}
    rows = browse_search_paths(db)
    # Explicit curriculum/grade names narrow only when they are present in the question.
    for name in ("curriculum", "level"):
        narrowed = [row for row in rows if contains_phrase(terms, words(row[name]))]
        if narrowed:
            rows = narrowed
    topic_matches = {row['topic_id'] for row in rows if contains_phrase(terms, words(row['topic']))}
    topic_phrases = {words(row['topic']) for row in rows if row['topic_id'] in topic_matches}
    # An exact topic name (Light) must not resolve instead to an unrelated
    # identically named leaf (Needs of Plants / Light). Precision is per parent,
    # so one matched leaf cannot discard other explicitly requested topics.
    precise = [row for row in rows if contains_phrase(terms, words(row['subtopic'] or ''))
               and (words(row['subtopic']) not in topic_phrases or words(row['topic']) == words(row['subtopic']))]
    precise_topics = {row['topic_id'] for row in precise}
    matches = [(row, True) for row in precise] + [(row, False) for row in rows
               if row['topic_id'] in topic_matches and row['topic_id'] not in precise_topics]
    paths = {}
    for row, is_precise in matches:
        leaf = row["subtopic_id"] if is_precise else None
        key = (row["topic_id"], leaf)
        paths[key] = {**{name: row[name] for name in ("curriculum_id", "curriculum_revision", "level_id",
            "subject_id", "domain_id", "topic_id")}, "subtopic_id": leaf,
            "label": " / ".join(str(row[name]) for name in ("curriculum", "level", "subject", "domain", "topic"))
                + (" / " + row["subtopic"] if leaf else "")}
    candidates = list(paths.values())
    return {"context": candidates[0] if len(candidates) == 1 else None,
            "candidates": candidates if len(candidates) > 1 else []}


def context(db, topic_id, subtopic_id, revision=None):
    path = describe_browse_path(db, topic_id, subtopic_id)
    if revision is not None and path["curriculum_revision"] != revision:
        fail(409, "curriculum_revision_changed")
    return path


def candidates(db, config, path, kind):
    if kind == "resource":
        return media_candidates(db, path["topic_id"], path["subtopic_id"], config)
    if kind == "tutor":
        return teacher_candidates(db, path["subject_id"], path["topic_id"])
    return kit_candidates(db, path["topic_id"], path["subtopic_id"], config)


def item(candidate):
    return {"id": str(candidate.id), "version": candidate.version, "kind": candidate.kind,
            "type": candidate.type, "title": candidate.title, "description": candidate.description,
            "availability_state": candidate.availability_state, "languages": candidate.languages,
            "grade_min": candidate.grade_min, "grade_max": candidate.grade_max,
            "mime_type": candidate.mime_type, "alt_text": candidate.alt_text,
            "has_thumbnail": candidate.card.get("has_thumbnail", False),
            "thumbnail_url": candidate.card.get("thumbnail_url"),
            "coverage": "subtopic" if candidate.precise_mapping else "topic" if candidate.kind != "tutor" else "expertise"}


def browse(db, config, path, kind, *, search="", media_type=None, language=None, offset=0, limit=24, focus_id=None):
    started = perf_counter()
    rows = [candidate for candidate in candidates(db, config, path, kind)
            if suitable(candidate, path["grade"], language)
            and (not media_type or candidate.type == media_type)
            and search.strip().casefold() in (candidate.title + " " + (candidate.description or "")).casefold()]
    rows.sort(key=lambda candidate: (candidate.title.casefold(), str(candidate.id)))
    if focus_id:
        position = next((index for index, candidate in enumerate(rows) if candidate.id == focus_id), None)
        if position is not None:
            offset = position // limit * limit
    result = {"items": [item(candidate) for candidate in rows[offset:offset + limit]], "total": len(rows),
              "offset": offset, "limit": limit, "curriculum_revision": path["curriculum_revision"]}
    LOGGER.info("explore_browse", extra={"fields": {"kind": kind, "eligible_count": len(rows),
                "returned_count": len(result["items"]), "duration_ms": round((perf_counter() - started) * 1000, 3)}})
    return result


def browse_curiosity(db, config, question, kind, *, search="", media_type=None, language=None,
                     offset=0, limit=24, focus_id=None):
    """Combine all matching published paths; filter and deduplicate before pagination."""
    resolved = curiosity_context(db, question)
    paths = [resolved["context"]] if resolved["context"] else resolved["candidates"]
    unique = {}
    for matched in paths:
        path = context(db, matched["topic_id"], matched["subtopic_id"], matched["curriculum_revision"])
        for candidate in candidates(db, config, path, kind):
            if (not suitable(candidate, path["grade"], language)
                    or media_type and candidate.type != media_type
                    or search.strip().casefold() not in (candidate.title + " " + (candidate.description or "")).casefold()):
                continue
            unique.setdefault((candidate.kind, candidate.id), {**item(candidate), "browse_path": path})
    rows = sorted(unique.values(), key=lambda row: (row["title"].casefold(), row["id"]))
    if focus_id:
        position = next((index for index, row in enumerate(rows) if row["id"] == str(focus_id)), None)
        if position is not None:
            offset = position // limit * limit
    return {"items": rows[offset:offset + limit], "total": len(rows), "offset": offset, "limit": limit}


def open_item(db, config, path, kind, candidate_id, version, language=None):
    selected = next((candidate for candidate in candidates(db, config, path, kind)
                     if candidate.id == candidate_id and suitable(candidate, path["grade"], language)), None)
    if selected is None:
        fail(404, "explore_item_unavailable")
    if selected.version != version:
        fail(409, "explore_version_changed")
    return {"item": {**selected.card, "version": selected.version}, "kind": selected.kind,
            "availability_state": selected.availability_state}
