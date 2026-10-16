"""Independent policy, compatibility and dependency-direction regression gates."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.contracts.catalogue import CatalogueCandidate
from app.contracts.decisions import Decision, TeachingContext
from app.contracts.math_templates import TEMPLATES
from app.modules.decision_engine import POLICY_VERSION
from app.modules.decision_engine.recommendation.selection import learning_need, select_recommendations
from app.modules.decision_engine.teaching.resolution import resolve
from app.modules.decision_engine.visual.mathematics import decide_visual
from app.modules.decision_engine.visual.simulation import select_engine
from b15_policy_snapshot import observations

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "app/modules/decision_engine"


def test_all_captured_decisions_match_pre_extraction_baseline():
    baseline = json.loads((Path(__file__).parent / "fixtures/b15-policy-baseline.json").read_text(encoding="utf-8"))
    actual = observations()
    # B16 intentionally changes default 3D routing and fixes plural visual opt-outs.
    # Preserve the historical extraction fixture; all other extraction behavior stays pinned.
    assert actual.pop("simulations") == [
        {**item, "engine": "three" if item["engine"] == "r3f" else None if item["question"].endswith("no animations") else item["engine"]}
        for item in baseline.pop("simulations")]
    assert actual == baseline
    assert POLICY_VERSION == "visual-keywords-4"


def test_engine_and_shared_contracts_have_no_application_dependencies():
    for path in [*ENGINE.rglob("*.py"), *(ROOT / "app/contracts").glob("*.py")]:
        is_engine = path.is_relative_to(ENGINE)
        allowed_app = ("app.contracts.", "app.modules.decision_engine.") if is_engine else ("app.contracts.",)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = [item.name for item in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) else []
            if isinstance(node, ast.ImportFrom):
                assert node.level == 0, f"Use auditable absolute imports: {path}"
            for name in names:
                assert not name.startswith(("fastapi", "sqlalchemy", "psycopg", "httpx", "requests")), (path, name)
                if name.startswith("app."):
                    assert name.startswith(allowed_app) or is_engine and name == "app.modules.decision_engine", (path, name)
                elif is_engine:
                    assert name.split(".")[0] in {"re", "json", "collections", "types", "uuid", "math"}, (path, name)
            if is_engine and isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"open", "__import__", "eval", "exec"}, (path, node.func.id)


def test_engine_imports_and_runs_in_an_isolated_process_without_infrastructure():
    source = '''
import builtins, importlib, pkgutil, sys
original = builtins.__import__
def guarded(name, *args, **kwargs):
    if name.startswith(("sqlalchemy", "fastapi", "psycopg", "httpx", "app.core")):
        raise AssertionError("Infrastructure dependency: " + name)
    if name.startswith("app.modules.") and not name.startswith("app.modules.decision_engine"):
        raise AssertionError("Application dependency: " + name)
    return original(name, *args, **kwargs)
builtins.__import__ = guarded
from app.modules import decision_engine
for item in pkgutil.walk_packages(decision_engine.__path__, decision_engine.__name__ + "."):
    importlib.import_module(item.name)
from app.modules.decision_engine.recommendation.selection import learning_need, select_recommendations
assert select_recommendations([], learning_need("Explain gravity", ""), "Explain gravity", "Gravity pulls.")["display_mode"] == "none"
assert not any(name.startswith(("sqlalchemy", "fastapi", "psycopg", "httpx")) for name in sys.modules)
'''
    subprocess.run([sys.executable, "-c", source], cwd=ROOT, check=True, capture_output=True, text=True)


def test_functional_candidate_services_do_not_import_decisions_or_coordinators():
    for name in ("resources", "teachers", "activity_kits"):
        path = ROOT / f"app/modules/functional/{name}/candidates.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
        assert not any(name.startswith(("app.modules.decision_engine", "app.modules.application.recommendations", "app.modules.application.learning_response")) for name in imports)


def test_compatibility_exports_refer_to_the_same_implementations_and_types():
    from app.modules.application.recommendations.selection import select_recommendations as old_rank
    from app.modules.application.recommendations.contracts import Decision as old_decision
    from app.modules.functional.curriculum.teaching_context import TeachingContext as old_context
    from app.modules.application.teaching.math_visuals import decide_visual as old_visual, TEMPLATES as old_registry
    from app.modules.application.teaching.simulations import select_engine as old_simulation
    from app.modules.application.teaching.profiles import profile as old_profile
    from app.modules.decision_engine.teaching.profiles import profile
    assert select_recommendations is old_rank
    assert Decision is old_decision and TeachingContext is old_context
    assert old_visual is decide_visual and old_simulation is select_engine and old_profile is profile
    assert old_registry is TEMPLATES


def test_ranking_is_order_independent_and_does_not_mutate_inputs():
    def candidate(number):
        return CatalogueCandidate(id=UUID(int=number), kind="resource", type="image", version=1,
            title="Gravity", description="Gravity pulls objects down.", availability_state="available", card={}).selection_data()
    pool = [candidate(2), candidate(1)]
    history = []
    need = learning_need("Explain gravity", "")
    before = deepcopy((pool, history, need))
    first = select_recommendations(pool, need, "Explain gravity", "Gravity pulls objects down.", history=history)
    second = select_recommendations(list(reversed(pool)), need, "Explain gravity", "Gravity pulls objects down.", history=history)
    assert first == second
    assert first["primary"]["candidate_id"] == str(UUID(int=1))
    assert (pool, history, need) == before
    # New persisted decisions keep their UUID and version validation boundary.
    assert Decision.model_validate(first).primary.candidate_id == UUID(int=1)
    invalid = deepcopy(first)
    invalid["primary"]["version"] = 0
    with pytest.raises(ValidationError):
        Decision.model_validate(invalid)


def test_profile_context_ambiguity_and_unknown_level_are_explicit():
    from app.modules.decision_engine.teaching.profiles import profile
    first = TeachingContext({"subtopic_id": UUID(int=1)}, {"curriculum": "A", "topic": "Gravity", "subtopic": "Falling"}, 1, None, None)
    second = TeachingContext({"subtopic_id": UUID(int=2)}, {**first.names, "curriculum": "B"}, 1, None, None)
    assert resolve("Explain gravity", [second, first]).candidates == (first, second)
    assert resolve("Explain evaporation", [first]).context is None
    assert profile(None, "Senior school").level is None
    assert profile(None, "Senior school").max_words == 100


def test_routing_is_repeatable_and_registry_cannot_be_mutated():
    decision = decide_visual("Explain fractions using pizza", 1)
    decision["allowed_templates"].clear()
    assert decide_visual("Explain fractions using pizza", 1)["allowed_templates"] == ["fraction_circle"]
    with pytest.raises(TypeError):
        TEMPLATES["fraction_circle"]["parameters"]["numerator"]["min"] = 99
    assert isinstance(TEMPLATES["trigonometric_function"]["parameters"]["function"]["options"], tuple)
    assert list((ROOT / "app").rglob("math_templates.json")) == [ROOT / "app/contracts/math_templates.json"]
