"""Single packaged trusted template registry; immutable after loading static data."""
import json
from importlib.resources import files
from types import MappingProxyType


def _freeze(value):
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


TEMPLATES = _freeze(json.loads(files("app.contracts").joinpath("math_templates.json").read_text(encoding="utf-8")))
