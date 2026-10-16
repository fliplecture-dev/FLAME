"""Nonblocking answer-followup coordination: catalogue first, generation separately."""
from uuid import UUID
from app.core.domain_errors import fail

from app.modules.functional.curriculum.public_paths import describe_browse_path
from app.modules.functional.resources.candidates import eligible_candidates
from app.modules.functional.resources.simulations import open_simulation
from app.modules.application.learning_response.explore import curiosity_context
from app.modules.decision_engine.visual.media import select_simulation


def library_simulation(db, config, question, *, context=None, saved_source=None, language=None):
    # Reopening a chosen simulation must recheck the same version, not silently rerank.
    if saved_source:
        if context is not None and (UUID(saved_source["topic_id"]) != context.ids["topic_id"]
                or (UUID(saved_source["subtopic_id"]) if saved_source.get("subtopic_id") else None) != context.ids.get("subtopic_id")
                or saved_source["revision"] != context.revision):
            fail(409, "unavailable_context")
        return open_simulation(db, config, UUID(saved_source["resource_id"]), topic_id=UUID(saved_source["topic_id"]),
            subtopic_id=UUID(saved_source["subtopic_id"]) if saved_source.get("subtopic_id") else None,
            revision=saved_source["revision"], version=saved_source["version"], language=language), saved_source
    if context is not None:
        paths = [{"topic_id": context.ids["topic_id"], "subtopic_id": context.ids.get("subtopic_id"),
                  "curriculum_revision": context.revision}]
    else:
        matched = curiosity_context(db, question)
        paths = [matched["context"]] if matched["context"] else matched["candidates"]
    pool, owners = [], {}
    for selected_path in paths:
        path = describe_browse_path(db, selected_path["topic_id"], selected_path["subtopic_id"])
        if path["curriculum_revision"] != selected_path["curriculum_revision"]:
            continue
        topic = path["topic_name"] + " " + path["subtopic_name"]
        candidate = select_simulation(eligible_candidates(db, path["topic_id"], path["subtopic_id"], config),
                                      question, topic=topic, grade=path["grade"], language=language)
        if candidate is not None:
            pool.append(candidate)
            owners[str(candidate.id)] = path
    topic = " ".join(filter(None, (context.names.get(key) for key in ("topic", "subtopic")))) if context else ""
    chosen = select_simulation(pool, question, topic=topic)
    if chosen is None:
        return None, None
    path = owners[str(chosen.id)]
    source = dict(resource_id=str(chosen.id), version=chosen.version, topic_id=str(path["topic_id"]),
                  subtopic_id=str(path["subtopic_id"]) if path["subtopic_id"] else None, revision=path["curriculum_revision"])
    return open_simulation(db, config, chosen.id, topic_id=path["topic_id"], subtopic_id=path["subtopic_id"],
                           revision=path["curriculum_revision"], version=chosen.version, language=language), source
