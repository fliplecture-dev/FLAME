"""Recommendation coordination over public catalogue/context interfaces and owned history."""
import logging
from time import perf_counter
from app.core.domain_errors import fail
from fastapi import HTTPException
from app.modules.conversations.recommendation_context import load_answer
from app.modules.curriculum.public_paths import describe_path
from app.modules.resources.candidates import eligible_candidates as media_candidates
from app.modules.teachers.candidates import eligible_candidates as teacher_candidates
from app.modules.activity_kits.candidates import eligible_candidates as kit_candidates
from app.modules.recommendations.repository import RecommendationRepository
from app.modules.recommendations.contracts import Decision
from app.modules.recommendations.selection import concepts, learning_need, select_recommendations
from app.modules.recommendations.image_selection import block_text, decide_image, description, is_visual, none, tokens

LOGGER = logging.getLogger("flame.recommendations")


def selected_items(decision):
    return [item for item in (decision.get("primary"), decision.get("alternative")) if item]


def empty(reason="No authorized current Study path."):
    return {"status": "no_results", "resources": [], "teachers": [], "image_decision": none(reason)}


def eligible(db, context, config):
    if context.mode != "study" or not context.subject_id or not context.topic_id:
        return None, []
    try:
        path = describe_path(db, context.topic_id, context.subtopic_id)
    except HTTPException:
        return None, []
    if (path["subject_id"] != context.subject_id or path["curriculum_id"] != context.curriculum_id or
            path["curriculum_revision"] != context.revision):
        return None, []
    return path, [*media_candidates(db, context.topic_id, context.subtopic_id, config),
        *teacher_candidates(db, context.subject_id, context.topic_id),
        *kit_candidates(db, context.topic_id, context.subtopic_id, config)]


def card(candidate):
    result = dict(candidate.card)
    if candidate.kind == "resource":
        result["alt_text"], result["caption_or_transcript"] = description(candidate)
    return result


def general_response(saved, candidates):
    decision = dict(saved.image_decision["recommendation_decision"])
    index = {(c.kind, str(c.id)): c for c in candidates}
    collections = {"resource": [], "tutor": [], "kit": []}
    for field in ("primary", "alternative"):
        item = decision.get(field)
        if not item:
            continue
        candidate = index.get((item["candidate_kind"], item["candidate_id"]))
        if candidate is None or candidate.version != item["version"]:
            decision[field] = None  # Never rewrite saved choices when availability/version changes.
            continue
        data = card(candidate)
        if candidate.kind == "tutor":
            data.update(version=candidate.version, availability_state=item["availability_state"])
        collections[candidate.kind].append(data)
    decision["display_mode"] = decision["primary"]["display_mode"] if decision.get("primary") else "none"
    image = {k: v for k, v in saved.image_decision.items() if k != "recommendation_decision"}
    if image.get("resource_id") not in {r["id"] for r in collections["resource"]}:
        image = none("Selected illustration is no longer eligible.")
    return {"status": "ok" if selected_items(decision) else "no_results", "resources": collections["resource"],
        "teachers": collections["tutor"], "kits": collections["kit"], "image_decision": image, "recommendation_decision": decision}


def history_for(rows, resources):
    history = []
    index = {str(c.id): c for c in resources}
    for row in rows:
        old = row.image_decision or {}
        if old.get("recommendation_decision"):
            history.extend({**item, "message_id": str(row.message_id)} for item in selected_items(old["recommendation_decision"]))
        elif old.get("resource_id"):
            history.append({**old, "candidate_id": old["resource_id"], "version": old.get("resource_version"), "message_id": str(row.message_id)})
        history.extend({"candidate_id": rid, "version": index[rid].version, "displayed": True,
            "display_mode": "optional card", "message_id": str(row.message_id)} for rid in row.resource_ids
            if rid in index and not old.get("recommendation_decision"))
    return history


def recommend(db, config, student_id, session_id, message_id):
    started = perf_counter()
    try:
        return _recommend(db, config, student_id, session_id, message_id)
    finally:
        LOGGER.info("recommendation_latency", extra={"fields": {"total_ms": round((perf_counter() - started) * 1000, 3)}})


def _recommend(db, config, student_id, session_id, message_id):
    context = load_answer(db, student_id, session_id, message_id)
    started = perf_counter()
    path, candidates = eligible(db, context, config)
    LOGGER.info("recommendation_retrieval", extra={"fields": {"retrieval_ms": round((perf_counter() - started) * 1000, 3), "eligible_count": len(candidates)}})
    if path is None:
        return empty()
    repo = RecommendationRepository(db)
    saved = repo.get(session_id, message_id)
    resources = [c for c in candidates if c.kind == "resource"]
    precise_ids = {str(c.id) for c in resources if c.precise_mapping}
    earlier = repo.earlier(session_id, context.earlier_message_ids)
    if saved is not None and (saved.image_decision or {}).get("recommendation_decision"):
        return general_response(saved, candidates)
    if saved is None:
        previous = next((block_text(q) for q in context.earlier_questions if concepts(block_text(q))), "")
        previous = previous or path["topic_name"] + (" " + path["subtopic_name"] if path["subtopic_name"] else "")
        question, answer = block_text(context.question_blocks), block_text(context.answer_blocks)
        need = learning_need(question, previous, context.inferred_need)
        ranking_started = perf_counter()
        raw = select_recommendations([c.selection_data() for c in candidates], need, question, answer,
            grade=path["grade"], history=history_for(earlier, resources), precise_ids=precise_ids)
        ranking_ms = round((perf_counter() - ranking_started) * 1000, 3)
        decision = Decision.model_validate(raw).model_dump(mode="json", exclude_none=True)
        # Preserve required nullable keys in the existing public and stored contract.
        decision.setdefault("primary", None); decision.setdefault("alternative", None)
        for item in selected_items(decision):
            item.setdefault("reference_message_id", None)
            selected = next((c for c in candidates if str(c.id) == item["candidate_id"] and c.kind == item["candidate_kind"] and c.version == item["version"]), None)
            if selected is None:
                fail(409, "recommendation_unavailable")
        items = selected_items(decision)
        image = next((i for i in items if i["candidate_type"] in {"image", "diagram"}), None)
        legacy = {**none("No selected inline illustration."), **({"resource_id": image["candidate_id"], "resource_version": image["version"],
            "display_mode": image["display_mode"], "reason": image["reason"], "reference_message_id": image["reference_message_id"]} if image else {})}
        saved = repo.create(context, [i["candidate_id"] for i in items if i["candidate_kind"] == "resource"],
            [i["candidate_id"] for i in items if i["candidate_kind"] == "tutor"], {**legacy, "recommendation_decision": decision})
        LOGGER.info("recommendation_decision", extra={"fields": {"message_id": str(message_id), "intent": need["intent"], "source": need["source"],
            "ranking_ms": ranking_ms, "eligible_count": len(candidates), "selected_count": len(items), "display_modes": [i["display_mode"] for i in items],
            "reason": "ranked_concept_intent" if items else "insufficient_match_or_suppressed"}})
        return general_response(saved, candidates)
    # Existing schema-1 decisions retain their original choices and response fields.
    if not saved.image_decision:
        previous = next((block_text(q) for q in context.earlier_questions if tokens(block_text(q))), "")
        saved.image_decision = decide_image(resources, block_text(context.question_blocks), block_text(context.answer_blocks),
            previous_question=previous, grade=path["grade"], objective=path["objective"], subtopic_ids=precise_ids,
            history=[{**r.image_decision, "message_id": str(r.message_id)} for r in earlier if r.image_decision])
    image = dict(saved.image_decision)
    resource_index = {str(c.id): c for c in resources}
    chosen = resource_index.get(image.get("resource_id"))
    if image.get("display_mode") != "none" and (chosen is None or chosen.version != image.get("resource_version")):
        image = none("Previously selected image is no longer eligible at its selected version.")
    shown = [dict(resource_index[rid].card) for rid in saved.resource_ids if rid in resource_index and not is_visual(resource_index[rid])]
    if image.get("display_mode") != "none" and chosen:
        shown.append(card(chosen))
    teachers = {str(c.id): c for c in candidates if c.kind == "tutor"}
    tutor_cards = [dict(teachers[tid].card) for tid in saved.teacher_ids if tid in teachers]
    return {"status": "ok" if shown or tutor_cards else "no_results", "resources": shown, "teachers": tutor_cards, "image_decision": image}


def mark_image(db, config, student_id, session_id, body):
    context = load_answer(db, student_id, session_id, body.message_id)
    saved = RecommendationRepository(db).get(session_id, body.message_id)
    decision = saved.image_decision if saved else None
    if not decision or decision.get("display_mode") != "inline" or decision.get("resource_id") != str(body.resource_id) or decision.get("resource_version") != body.resource_version:
        fail(409, "invalid_image_decision")
    path, candidates = eligible(db, context, config)
    if path is None:
        fail(409, "unavailable_context")
    if not any(c.id == body.resource_id and c.version == body.resource_version and is_visual(c) for c in candidates):
        fail(409, "invalid_image_decision")
    displayed = body.display_status == "displayed" or decision.get("displayed", False)
    updated = {**decision, "displayed": displayed, "failed": body.display_status == "failed" and not displayed}
    if decision.get("recommendation_decision"):
        general = dict(decision["recommendation_decision"])
        for field in ("primary", "alternative"):
            item = general.get(field)
            if item and item["candidate_id"] == str(body.resource_id):
                success = body.display_status == "displayed" or item.get("displayed", False)
                general[field] = {**item, "displayed": success, "failed": body.display_status == "failed" and not success}
        updated["recommendation_decision"] = general
    saved.image_decision = updated
    return {"status": "ok"}


def mark_card(db, config, student_id, session_id, body):
    current = recommend(db, config, student_id, session_id, body.message_id)
    valid = next((i for i in selected_items(current.get("recommendation_decision", {})) if i["candidate_id"] == str(body.candidate_id)
        and i["version"] == body.version and i["display_mode"] == "optional card"), None)
    if not valid:
        fail(409, "recommendation_unavailable")
    saved = RecommendationRepository(db).get(session_id, body.message_id)
    general = dict(saved.image_decision["recommendation_decision"])
    for field in ("primary", "alternative"):
        if general.get(field) and general[field]["candidate_id"] == str(body.candidate_id):
            general[field] = {**general[field], "displayed": True}
    saved.image_decision = {**saved.image_decision, "recommendation_decision": general}
    return {"status": "ok"}


def open_candidate(db, config, student_id, session_id, candidate_id, message_id):
    current = recommend(db, config, student_id, session_id, message_id)
    choice = next((i for i in selected_items(current.get("recommendation_decision", {})) if i["candidate_id"] == str(candidate_id)), None)
    if not choice:
        fail(404, "recommendation_unavailable")
    collection = {"resource": "resources", "kit": "kits", "tutor": "teachers"}[choice["candidate_kind"]]
    return {"decision": choice, "item": next(r for r in current[collection] if r["id"] == str(candidate_id))}
