import json
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.teaching.math_visuals import TEMPLATES, MathVisualBlock, decide_visual, apply_decision
from app.modules.teaching.answer_service import _answer
from app.modules.teaching.gateway import Generated, GatewayError
from app.modules.teaching.rich_answer import parse_blocks, readable
from app.modules.teaching.prompt import assemble_open_curiosity


def block(template="fraction_bar"):
    return dict(kind="math_visual", version=1, template=template, title="Explore mathematics",
                description="An illustrative activity.", parameters={k:v["default"] for k,v in TEMPLATES[template]["parameters"].items()})


@pytest.mark.parametrize("template", list(TEMPLATES))
def test_all_trusted_templates_validate_and_project_history(template):
    value=block(template)
    parsed=parse_blocks(json.dumps(dict(format="flame-rich-1", blocks=[value])))
    assert parsed[0]["template"] == template
    assert template in readable(parsed)
    assert "Saved initial activity" in readable(parsed)


@pytest.mark.parametrize("question,level,mode,template,engine", [
    ("Show 12 objects in groups of 3",1,"math","counting_groups","konva"),
    ("Explain 3/4 with a fraction bar",2,"math","fraction_bar","konva"),
    ("Show a pizza split into quarters",2,"math","fraction_circle","konva"),
    ("Draw a triangle shape",0,"math","shape_explorer","konva"),
    ("Drag triangle vertices and inspect angles",3,"math","triangle_angles","jsxgraph"),
    ("Construct a perpendicular bisector",4,"math","perpendicular_bisector","jsxgraph"),
    ("Show perpendicular lines",4,"math","perpendicular_lines","jsxgraph"),
    ("Explore parallel lines",4,"math","parallel_lines","jsxgraph"),
    ("Explore a circle radius",3,"math","circle_geometry","jsxgraph"),
    ("Plot a coordinate point",4,"math","coordinate_points","mafs"),
    ("Explore how slope changes a line",4,"math","linear_function","mafs"),
    ("Graph a quadratic function",5,"math","quadratic_function","mafs"),
    ("Plot y = sin x",5,"math","trigonometric_function","mafs"),
    ("Graph y = cos(x)",5,"math","trigonometric_function","mafs"),
    ("Plot a sine graph",None,"math","trigonometric_function","mafs"),
    ("Draw a triangle with angles 60°, 60° and 60°",None,"math","triangle_angles","jsxgraph"),
    ("Graph a quadratic function",1,"text",None,None),
    ("Compare monthly rainfall",3,"chart",None,None),
    ("Explain fractions with text only",3,"text",None,None),
    ("Why is the sky blue?",None,"auto",None,None),
    ("Explain what a graph is",None,"auto",None,None),
    ("समझाइए तीन चौथाई",None,"auto",None,None),
])
def test_decision_uses_learning_goal_not_library_names(question,level,mode,template,engine):
    result=decide_visual(question,level)
    assert (result["mode"],result["preferred_template"]) == (mode,template)
    if template:
        assert TEMPLATES[template]["engine"] == engine and result["allowed_templates"] == [template]


def test_same_call_semantic_selection_is_bounded_by_server_policy():
    visual={**block("quadratic_function"),"id":"v"}
    prose=dict(id="text",kind="markdown",text="A simple explanation.")
    assert apply_decision([prose,visual],decide_visual("Explain a quadratic",1)) == [prose]
    assert apply_decision([visual],decide_visual("text only",None))[0]["kind"] == "markdown"
    assert apply_decision([prose,visual],decide_visual("Explain this function",None))[-1] == visual
    assert len(apply_decision([visual,visual],decide_visual("Graph a quadratic",None))) == 1
    decision=decide_visual("Show this activity",4,[dict(assistant=[{**block("linear_function"),"id":"v"}])])
    assert decision["preferred_template"] == "linear_function"
    prompt=assemble_open_curiosity("Explore slope",[])
    assert prompt.rendering_decision["preferred_template"] == "linear_function"
    assert '"math_visual"' in prompt.messages[0]["content"]


@pytest.mark.parametrize("change", [
    dict(version=2),dict(version=True),dict(template="unknown"),dict(engine="eval"),dict(parameters=dict(numerator=2,denominator=0)),
    dict(parameters=dict(numerator=5,denominator=4)),dict(parameters=dict(numerator=True,denominator=4)),
    dict(parameters=dict(numerator="2",denominator=4)),dict(parameters=dict(numerator=1.2,denominator=4)),
    dict(parameters=dict(numerator=float("nan"),denominator=4)),
    dict(parameters=dict(numerator=10**500,denominator=4)),
])
def test_invalid_specs_fail_atomically(change):
    value={**block(),**change}
    with pytest.raises(ValidationError): MathVisualBlock(id="v",**value)
    with pytest.raises(GatewayError): _answer(uuid4(),None,Generated(json.dumps(dict(format="flame-rich-1",blocks=[value])),"stub",1,10))


def test_registry_parity_with_frontend():
    frontend=Path(__file__).resolve().parents[2]/"web/src/features/learning/math-templates.json"
    if frontend.exists(): assert json.loads(frontend.read_text(encoding="utf-8")) == TEMPLATES


def test_initial_geometry_constraints_and_saved_followup():
    triangle=block("triangle_angles");triangle["parameters"].update(cx=0,cy=-2)
    with pytest.raises(ValidationError): MathVisualBlock(id="v",**triangle)
    line=block("number_line");line["parameters"]["value"]=20
    with pytest.raises(ValidationError): MathVisualBlock(id="v",**line)
    parsed=parse_blocks(json.dumps(dict(format="flame-rich-1",blocks=[block()])))
    prompt=assemble_open_curiosity("Explain that activity",[dict(user=[dict(kind="text",text="Explore fractions")],assistant=parsed)])
    assert prompt.rendering_decision["preferred_template"] == "fraction_bar"
    assert any("numerator" in m["content"] for m in prompt.messages if m["role"]=="assistant")


def test_long_questions_trim_history_for_template_instruction_overhead():
    history=[dict(user=[dict(kind="text",text="earlier question "*120)],
                  assistant=[dict(kind="markdown",text="earlier explanation "*100)]) for _ in range(8)]
    prompt=assemble_open_curiosity("x"*4000,history)
    assert prompt.messages[-1]["content"] == "x"*4000
    assert sum(len(m["content"].encode("utf-8"))+32 for m in prompt.messages) <= 16000
    assert any(m["role"]=="assistant" for m in prompt.messages)
