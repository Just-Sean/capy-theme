"""The catalog of built-in daisyUI themes that capy-theme themes start from.

The values come from builtin_themes.json, which is generated from the daisyUI
package by scripts/generate_builtin_themes.py (don't edit it by hand). A project
can limit which built-in themes are offered with:

    CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]

Unset (the default) offers all of them.
"""

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from django.core.exceptions import ImproperlyConfigured

from .. import conf

_DATA = json.loads(Path(__file__).with_name("builtin_themes.json").read_text(encoding="utf-8"))
DAISYUI_VERSION = _DATA["daisyui_version"]
# name -> {"scheme": "light" or "dark", "values": {CSS variable: value}}
THEMES = _DATA["themes"]


@dataclass(frozen=True)
class BuiltinTheme:
    """One built-in daisyUI theme."""

    name: str
    scheme: str  # "light" or "dark"
    values: MappingProxyType  # CSS variable -> value, e.g. "--color-primary" -> "oklch(...)"

    @property
    def is_dark(self):
        return self.scheme == "dark"


_ALL = tuple(
    BuiltinTheme(name=name, scheme=theme["scheme"], values=MappingProxyType(theme["values"]))
    for name, theme in THEMES.items()
)


def get_builtin_themes():
    """Return the built-in themes this project offers, in daisyUI's order.

    Limited by the optional CAPY_THEME_BUILTIN_THEMES setting (a list of theme
    names). Raises ImproperlyConfigured if it names a theme that doesn't exist.
    """
    allowed = conf.get("CAPY_THEME_BUILTIN_THEMES")
    if allowed is None:
        return list(_ALL)

    unknown = sorted(set(allowed) - set(THEMES))
    if unknown:
        raise ImproperlyConfigured(
            f"CAPY_THEME_BUILTIN_THEMES names unknown daisyUI themes: {', '.join(unknown)}. "
            f"Available: {', '.join(THEMES)}."
        )
    return [theme for theme in _ALL if theme.name in allowed]


def builtin_values(name):
    """Return a copy of a built-in theme's values, or None if there's no such theme.

    Not limited by CAPY_THEME_BUILTIN_THEMES: it's used to copy values into
    revisions, not to offer choices.
    """
    theme = THEMES.get(name)
    return dict(theme["values"]) if theme else None
