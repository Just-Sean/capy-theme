"""Validation for theme data.

Theme.settings is checked against settings.schema.json, a standard JSON Schema
file that each phase extends as it adds settings.
"""

import json
import math
from functools import cache
from pathlib import Path

from django.core.exceptions import ValidationError
from jsonschema import Draft202012Validator

from .catalog import get_builtin_themes

SCHEMA_PATH = Path(__file__).with_name("settings.schema.json")


@cache
def settings_validator():
    """Return a validator for settings.schema.json (loaded once)."""
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_settings(value):
    """Raise ValidationError listing every problem if value doesn't match the schema."""
    errors = sorted(settings_validator().iter_errors(value), key=lambda error: list(error.path))
    messages = [_describe(error) for error in errors] + _not_finite(value)
    if messages:
        raise ValidationError(messages, code="invalid_settings")


def _not_finite(value, path=""):
    """Messages for NaN and infinite numbers, which JSON Schema's limits let through.

    Python reads the JSON literals NaN and Infinity, and every comparison with NaN
    is false, so a minimum or maximum never refuses it (#240).
    """
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{path}: {value} isn't a number." if path else f"{value} isn't a number."]
    if isinstance(value, dict):
        items = value.items()
    elif isinstance(value, list):
        items = enumerate(value)
    else:
        return []
    return [
        message
        for key, item in items
        for message in _not_finite(item, f"{path}/{key}" if path else str(key))
    ]


def _describe(error):
    location = "/".join(str(part) for part in error.path)
    return f"{location}: {error.message}" if location else error.message


def validate_base(name):
    """Raise ValidationError unless name is an offered built-in daisyUI theme."""
    names = {theme.name for theme in get_builtin_themes()}
    if name not in names:
        raise ValidationError(f"{name!r} is not an available daisyUI theme.", code="invalid_base")
