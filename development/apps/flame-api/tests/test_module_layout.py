"""Layer direction, canonical model identity and pre-move API/schema compatibility."""
import ast
import copy
import hashlib
import importlib
import json
from pathlib import Path

from sqlalchemy.dialects.postgresql import dialect
from sqlalchemy.schema import CreateIndex, CreateTable

from app.core.config import Settings
from app.core.database import Base
from app.main import create_app
from app.modules.functional.model_registry import MODEL_MODULES, register_models

ROOT = Path(__file__).resolve().parents[1]
MODULES = ROOT / "app/modules"


def imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            yield node.module or ""
        elif isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)


def test_functional_owners_do_not_depend_on_coordination_or_policies():
    for path in (MODULES / "functional").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for name in imports(tree):
            assert not name.startswith(("app.modules.application", "app.modules.decision_engine")), (path, name)
        # Dynamic application imports cannot bypass the dependency rule.
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                assert not node.value.startswith(("app.modules.application.", "app.modules.decision_engine.")), (path, node.value)


def test_only_the_three_canonical_layers_exist_and_imports_use_them():
    assert {p.name for p in MODULES.iterdir() if p.is_dir() and p.name != "__pycache__"} == {
        "functional", "application", "decision_engine",
    }
    for folder in (ROOT / "app", ROOT / "scripts", ROOT / "tests", ROOT / "migrations"):
        for path in folder.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for name in imports(tree):
                if name.startswith("app.modules."):
                    assert name.split(".")[2] in {"functional", "application", "decision_engine"}, (path, name)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and node.value.startswith("app.modules.") and node.value.split(".")[2]:
                    assert node.value.split(".")[2] in {"functional", "application", "decision_engine"}, (path, node.value)
    for path in MODULES.rglob("__init__.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(isinstance(node, (ast.Import, ast.ImportFrom, ast.Call)) for node in ast.walk(tree)), path


def test_orm_declarations_have_one_functional_owner_and_idempotent_registration():
    register_models()
    original = dict(Base.metadata.tables)
    register_models()
    assert set(original) == set(Base.metadata.tables)
    assert all(Base.metadata.tables[key] is value for key, value in original.items())
    for name in MODEL_MODULES:
        assert name.startswith("app.modules.functional.")
        assert importlib.import_module(name).__name__ == name
    for path in (MODULES / "application").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        assert not any(isinstance(node, ast.Name) and node.id == "__tablename__" for node in ast.walk(tree)), path
        assert not any(name.startswith("app.modules.functional.") and name.endswith(".repository") for name in imports(tree)), path
    for relative in ("app/main.py", "migrations/env.py"):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        assert "app.modules.functional.model_registry" in set(imports(tree))
        assert any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "register_models" for node in ast.walk(tree))


def test_public_api_and_postgresql_schema_match_the_pre_move_baseline():
    # No live database: compile the full declarations and inspect the application contract.
    app = create_app(Settings(_env_file=None, environment="test", database_url=None))
    api = app.openapi()
    assert app.openapi() is api  # Cached calls keep stable names and valid references.
    # B17 adds independent discovery routes/table and an optional item reference.
    # Keep the original B15 golden contract intact for every pre-existing declaration.
    api = copy.deepcopy(api)
    added_paths = [path for path in api["paths"] if path.startswith(("/api/v1/catalogue", "/api/v1/admin/catalogue"))]
    assert len(added_paths) == 5
    for path in added_paths:
        del api["paths"][path]
    # Guest access/profile is additive; project only its known additions away.
    for path in list(api["paths"]):
        if path.startswith("/api/v1/guest/") or path in ("/api/v1/me/profile", "/api/v1/me/usage"):
            del api["paths"][path]
    schemas = api["components"]["schemas"]
    for name in ("GuestSessionInput", "GuestAnswer", "ProfileEdit"):
        del schemas[name]
    for name in ("RegisterBody", "LoginBody"):
        del schemas[name]["properties"]["phone_number"]
    for name in ("CatalogueReference", "EntryDraft", "EntryEdit", "Publication"):
        del schemas[name]
    del schemas["AnswerRequest"]["properties"]["catalogue_item"]
    ddl = []
    contact_fields = ("phone_number ", "contact_number ", "address ", "city ", "state ", "country ", "pincode ")
    for name, table in sorted(Base.metadata.tables.items()):
        if name in ("flame.catalogue_entries", "flame.guest_access"):
            continue
        definition = str(CreateTable(table).compile(dialect=dialect()))
        if name == "flame.student_profiles":
            definition = "".join(line for line in definition.splitlines(keepends=True) if not line.lstrip().startswith(contact_fields))
        ddl.append(definition)
        ddl.extend(sorted(str(CreateIndex(index).compile(dialect=dialect())) for index in table.indexes))
    def digest(value):
        return hashlib.sha256(value.encode()).hexdigest()
    actual = dict(openapi_sha256=digest(json.dumps(api, sort_keys=True)),
        schema_sha256=digest("\n".join(ddl)), table_count=len(Base.metadata.tables) - 2, path_count=len(api["paths"]))
    baseline = json.loads((ROOT / "tests/fixtures/module-layout-baseline.json").read_text(encoding="utf-8"))
    assert actual == baseline
