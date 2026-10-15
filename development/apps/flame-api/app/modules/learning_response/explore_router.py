"""Authenticated catalogue exploration independent of answer selection."""
from typing import Annotated, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from app.modules.identity.dependencies import require_member
from app.modules.conversations.recommendation_context import load_answer
from app.core.domain_errors import fail
from app.modules.learning_response import explore

router = APIRouter(prefix="/api/v1/explore", tags=["explore"])
Member = Annotated[dict, Depends(require_member)]
Kind = Literal["resource", "tutor", "kit"]


@router.get("/context")
def answer_context(request: Request, member: Member, session_id: UUID, message_id: UUID):
    with request.app.state.database.session() as db:
        saved = load_answer(db, UUID(member["id"]), session_id, message_id)
        if saved.mode == "curiosity":
            question = " ".join(str(block.get("text", "")) for block in saved.question_blocks if block.get("kind") == "text")
            return explore.curiosity_context(db, question)
        if not saved.topic_id:
            return {"context": None}
        path = explore.context(db, saved.topic_id, saved.subtopic_id, saved.revision)
        if path["curriculum_id"] != saved.curriculum_id or path["subject_id"] != saved.subject_id:
            fail(409, "explore_path_unavailable")
        return {"context": path}


@router.get("")
def browse(request: Request, _: Member, topic_id: UUID, kind: Kind = "resource", subtopic_id: UUID | None = None,
           curriculum_revision: int | None = Query(None, ge=1), search: str = Query("", max_length=200),
           media_type: str | None = Query(None, max_length=30), language: str | None = Query(None, max_length=35),
           offset: int = Query(0, ge=0, le=100000), limit: int = Query(24, ge=1, le=50), focus_id: UUID | None = None):
    with request.app.state.database.session() as db:
        path = explore.context(db, topic_id, subtopic_id, curriculum_revision)
        return explore.browse(db, request.app.state.settings, path, kind, search=search,
                              media_type=media_type, language=language, offset=offset, limit=limit, focus_id=focus_id)


@router.get("/summary")
def answer_resource_summary(request: Request, member: Member, session_id: UUID, message_id: UUID):
    with request.app.state.database.session() as db:
        saved = load_answer(db, UUID(member["id"]), session_id, message_id)
        if saved.mode == "curiosity":
            question = " ".join(str(block.get("text", "")) for block in saved.question_blocks if block.get("kind") == "text")
            resolved = explore.curiosity_context(db, question)
            matched = [resolved["context"]] if resolved["context"] else resolved["candidates"]
            paths = [explore.context(db, row["topic_id"], row["subtopic_id"], row["curriculum_revision"]) for row in matched]
        elif saved.topic_id:
            path = explore.context(db, saved.topic_id, saved.subtopic_id, saved.revision)
            if path["curriculum_id"] != saved.curriculum_id or path["subject_id"] != saved.subject_id:
                fail(409, "explore_path_unavailable")
            paths = [path]
        else:
            paths = []
        return JSONResponse(explore.resource_counts(db, request.app.state.settings, paths), headers={"Cache-Control": "no-store"})


@router.get("/curiosity")
def browse_curiosity(request: Request, member: Member, session_id: UUID, message_id: UUID, kind: Kind = "resource",
                     search: str = Query("", max_length=200), media_type: str | None = Query(None, max_length=30),
                     language: str | None = Query(None, max_length=35), offset: int = Query(0, ge=0, le=100000),
                     limit: int = Query(24, ge=1, le=50), focus_id: UUID | None = None):
    with request.app.state.database.session() as db:
        saved = load_answer(db, UUID(member["id"]), session_id, message_id)
        if saved.mode != "curiosity":
            fail(404, "explore_path_unavailable")
        question = " ".join(str(block.get("text", "")) for block in saved.question_blocks if block.get("kind") == "text")
        return explore.browse_curiosity(db, request.app.state.settings, question, kind, search=search,
            media_type=media_type, language=language, offset=offset, limit=limit, focus_id=focus_id)


@router.get("/{kind}/{candidate_id}")
def open_item(request: Request, _: Member, kind: Kind, candidate_id: UUID, topic_id: UUID,
              version: int = Query(ge=1), subtopic_id: UUID | None = None,
              curriculum_revision: int | None = Query(None, ge=1), language: str | None = Query(None, max_length=35)):
    with request.app.state.database.session() as db:
        path = explore.context(db, topic_id, subtopic_id, curriculum_revision)
        return explore.open_item(db, request.app.state.settings, path, kind, candidate_id, version, language)
