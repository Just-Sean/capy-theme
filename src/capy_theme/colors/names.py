"""The 20 daisyUI colors: names, groups and labels, and a theme's overrides."""

import json
from pathlib import Path

_DATA = json.loads(Path(__file__).with_name("colors.json").read_text(encoding="utf-8"))

# From colors.json: the editor's and admin's groups of the 20 colors.
COLOR_GROUPS = _DATA["groups"]


COLOR_NAMES = [name for names in COLOR_GROUPS.values() for name in names]


# Labels that differ from the color's name.
COLOR_LABELS = _DATA["labels"]


def label(name):
    """A readable label for a color, e.g. "Primary text" for primary-content."""
    if name in COLOR_LABELS:
        return COLOR_LABELS[name]
    if name.endswith("-content"):
        return f"{name.removesuffix('-content').capitalize()} text"
    return name.capitalize()


def overrides(settings):
    """Return {name: value} of the theme's overridden colors from its settings."""
    return dict(settings.get("colors", {}))


# Colors with a text ("-content") color.
WITH_CONTENT = _DATA["with_content"]
