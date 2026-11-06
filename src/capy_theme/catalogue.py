"""The catalogue of built-in daisyUI themes that capy-theme themes start from.

The values come from builtin_themes.py, which is generated from the daisyUI
package. A project can limit which built-in themes are offered with:

    CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]

Unset (the default) offers all of them.
"""

from dataclasses import dataclass
from types import MappingProxyType

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .builtin_themes import THEMES


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
    allowed = getattr(settings, "CAPY_THEME_BUILTIN_THEMES", None)
    if allowed is None:
        return list(_ALL)

    unknown = sorted(set(allowed) - set(THEMES))
    if unknown:
        raise ImproperlyConfigured(
            f"CAPY_THEME_BUILTIN_THEMES names unknown daisyUI themes: {', '.join(unknown)}. "
            f"Available: {', '.join(THEMES)}."
        )
    return [theme for theme in _ALL if theme.name in allowed]
