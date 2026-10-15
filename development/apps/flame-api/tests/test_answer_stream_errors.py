import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.modules.teaching import answer_router
from app.modules.teaching.schemas import AnswerRequest


@pytest.mark.parametrize("detail,status,expected", [
    ("daily_limit_reached", 429, "daily_limit_reached"),
    ("request_in_progress", 409, "request_in_progress"),
    ("unavailable_context", 409, "unavailable_context"),
    ("private database or user information", 500, "answer_unavailable"),
])
def test_stream_preserves_safe_rejection_without_echoing_private_details(monkeypatch, detail, status, expected):
    monkeypatch.setattr(answer_router, "owned", lambda *args: None)
    def reject(*args, **kwargs):
        raise HTTPException(status, detail)
    monkeypatch.setattr(answer_router, "ask", reject)
    state = SimpleNamespace(database=MagicMock(), gateway=MagicMock(),
                            settings=SimpleNamespace(llm_daily_request_limit=100))
    request = SimpleNamespace(app=SimpleNamespace(state=state), state=SimpleNamespace(request_id="fixture"))
    response = answer_router.ask_stream(request, uuid4(),
        AnswerRequest(question="Hello", mode="curiosity"), {"id": str(uuid4())}, "fixture-key")
    async def collect():
        return [json.loads(chunk) async for chunk in response.body_iterator]
    events = asyncio.run(collect())
    assert events[-1] == {"type": "failure", "code": expected, "status": status}
    assert "private database" not in json.dumps(events)
