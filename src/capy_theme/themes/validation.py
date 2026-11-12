"""Validation for theme data.

Theme.settings is checked against settings.schema.json, a standard JSON Schema
file that each phase extends as it adds settings.
"""

import json
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
    if errors:
        raise ValidationError([_describe(error) for error in errors], code="invalid_settings")


def _describe(error):
    location = "/".join(str(part) for part in error.path)
    return f"{location}: {error.message}" if location else error.message


def validate_base(name, scheme):
    """Raise ValidationError unless name is an offered built-in theme of this scheme."""
    names = {theme.name for theme in get_builtin_themes() if theme.scheme == scheme}
    if name not in names:
        raise ValidationError(
            f"{name!r} is not an available {scheme} daisyUI theme.", code="invalid_base"
        )
