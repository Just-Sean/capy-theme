"""daisyUI's shape and effect settings, overridden for both light and dark.

Stored in Theme.settings["shape"], e.g. {"radius_box": 0, "border": 2, "depth": False}.
Anything not set comes from the base theme.
"""

import json
from pathlib import Path

_DATA = json.loads(Path(__file__).with_name("shape.json").read_text(encoding="utf-8"))

# From shape.json. name: (CSS variable, unit, min, max, label, help)
SIZES = {
    name: (s["variable"], s["unit"], s["min"], s["max"], s["label"], s["help"])
    for name, s in _DATA["sizes"].items()
}
# name: (CSS variable, label, help)
EFFECTS = {name: (e["variable"], e["label"], e["help"]) for name, e in _DATA["effects"].items()}
SHAPE_NAMES = [*SIZES, *EFFECTS]


def shape_values(settings):
    """Return {CSS variable: value} for the shape settings a theme overrides."""
    chosen = settings.get("shape", {})
    values = {}
    for name, (variable, unit, *_rest) in SIZES.items():
        if name in chosen:
            values[variable] = f"{_number(chosen[name])}{unit}"
    for name, (variable, *_rest) in EFFECTS.items():
        if name in chosen:
            values[variable] = "1" if chosen[name] else "0"
    return values


def _number(value):
    text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    return text or "0"
