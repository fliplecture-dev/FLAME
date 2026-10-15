"""F11 rich data validation, policy projection and backwards compatibility."""
import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.teaching.answer_service import _answer
from app.modules.teaching.gateway import Generated, GatewayError
from app.modules.teaching.prompt import assemble_open_curiosity
from app.modules.teaching.rich_answer import parse_blocks, readable
from app.modules.teaching.schemas import ChartBlock, DirectAnswer
from app.modules.recommendations.learning_need import split_intent


def chart():
    return dict(kind="chart", chartType="line", title="Distance", description="At two metres per second.",
                xKey="seconds", xLabel="Seconds", yLabel="Metres", illustrative=True,
                series=[dict(key="metres", label="Distance")],
                data=[dict(seconds=0, metres=0), dict(seconds=1, metres=2)])


def rich(*blocks):
    return json.dumps(dict(format="flame-rich-1", blocks=list(blocks)))


def test_markdown_and_legacy_blocks_and_separate_intent():
    text, need = split_intent(rich(dict(kind="markdown", text="**Distance** $$d=vt$$"), chart()) +
        '<flame-intent>{"intent":"demonstrate","concept":"distance","language":"en"}</flame-intent>')
    result = DirectAnswer.model_validate(_answer(uuid4(), None, Generated(text, "stub", 1, 100)))
    assert [b.kind for b in result.blocks] == ["markdown", "chart"]
    assert len({b.id for b in result.blocks}) == 2
    assert result.grounded is False and need["intent"] == "demonstrate"
    assert parse_blocks('Plain **Markdown**.')[0]["kind"] == "markdown"
    source = '```json\n{"example":2}\n```'
    assert parse_blocks(source)[0]["text"] == source
    assert DirectAnswer(response_id=uuid4(), request_id=uuid4(), curriculum_version=None,
                        blocks=[dict(id="old", kind="text", text="$5 stays literal")]).blocks[0].kind == "text"


@pytest.mark.parametrize("mutate", [
    lambda c: c.update(chartType="script"),
    lambda c: c["data"][0].update(metres=True),
    lambda c: c["data"][0].update(metres="2"),
    lambda c: c["data"][0].update(metres=float("nan")),
    lambda c: c["data"][0].update(metres=float("inf")),
    lambda c: c["data"][0].update(metres=1e13),
    lambda c: c["data"][0].update(extra=1),
    lambda c: c.update(series=[dict(key="seconds", label="Bad")]),
    lambda c: c.update(series=[dict(key="constructor", label="Bad")]),
    lambda c: c.update(data=c["data"] * 26),
    lambda c: c.update(onClick="alert(1)"),
    lambda c: c.update(chartType="pie", data=[dict(seconds="A", metres=-1)]),
    lambda c: c.update(chartType="pie", data=[dict(seconds="A", metres=0)]),
])
def test_chart_rejects_malformed_or_executable_data(mutate):
    block = chart()
    mutate(block)
    with pytest.raises(ValidationError):
        ChartBlock(id="chart", **block)
    with pytest.raises(GatewayError, match="invalid_provider_output"):
        parse_blocks(rich(block))


@pytest.mark.parametrize("text", [
    '{"format":"flame-rich-1","blocks":[]}',
    '{"format":"flame-rich-1","blocks":[',
    '{"format":"flame-rich-1","format":"flame-rich-1","blocks":[]}',
    rich(dict(kind="markdown", text="Fine", grounded=True)),
    rich(dict(kind="markdown", text="Fine", id="model-owned")),
    rich(dict(kind="markdown", text="x"))[:-1],
])
def test_rich_output_fails_atomically(text):
    with pytest.raises(GatewayError):
        _answer(uuid4(), None, Generated(text, "stub", 2, 10))


def test_word_and_authority_guards_include_chart_labels():
    block = chart()
    with pytest.raises(GatewayError):
        _answer(uuid4(), None, Generated(rich(block), "stub", 1, 10), max_words=1)
    block["description"] = " ".join(["long"] * 30)
    with pytest.raises(GatewayError):
        _answer(uuid4(), None, Generated(rich(block), "stub", 1, 10), max_words=20)
    block["description"] = "I verified your textbook."
    from app.modules.teaching.output_guard import has_forbidden_authority_claim
    # Exercise exactly the same shared authority policy, including escaped JSON text.
    assert has_forbidden_authority_claim(readable([block]))
    with pytest.raises(GatewayError):
        _answer(uuid4(), None, Generated(rich(block), "stub", 1, 10))


def test_follow_up_includes_markdown_charts_and_old_tables_within_budget():
    blocks = parse_blocks(rich(dict(kind="markdown", text="Distance is speed times time."), chart()))
    history = [dict(user=[dict(kind="text", text="How far?")], assistant=blocks)]
    prompt = assemble_open_curiosity("What about two seconds?", history)
    assistant = next(m["content"] for m in prompt.messages if m["role"] == "assistant")
    assert "speed times time" in assistant and "Distance" in assistant and "2.0" in assistant
    assert "flame-rich-1" in prompt.messages[0]["content"]
    assert "A B 1 2" in readable([dict(kind="table", columns=["A", "B"], rows=[["1", "2"]])])


def test_all_chart_types_accept_finite_data():
    for kind in ("bar", "line", "pie"):
        block = chart()
        block["chartType"] = kind
        assert ChartBlock(id="chart", **block).chartType == kind
