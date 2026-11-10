"""daisyUI's shape and effect settings, overridden for both light and dark.

Stored in Theme.settings["shape"], e.g. {"radius_box": 0, "border": 2, "depth": False}.
Anything not set comes from the base theme.
"""

# name: (CSS variable, unit, minimum, maximum, label, help)
SIZES = {
    "radius_selector": (
        "--radius-selector",
        "rem",
        0,
        2,
        "Small corner radius",
        "Checkboxes, toggles and badges. 0 is square.",
    ),
    "radius_field": (
        "--radius-field",
        "rem",
        0,
        2,
        "Field corner radius",
        "Buttons, inputs, selects and tabs. 0 is square.",
    ),
    "radius_box": (
        "--radius-box",
        "rem",
        0,
        3,
        "Box corner radius",
        "Cards, alerts, modals and other boxes. 0 is square.",
    ),
    "size_selector": (
        "--size-selector",
        "rem",
        0.125,
        0.5,
        "Small control size",
        "Base size of checkboxes, toggles and badges (daisyUI uses 0.1875–0.3125).",
    ),
    "size_field": (
        "--size-field",
        "rem",
        0.125,
        0.5,
        "Field size",
        "Base size of buttons and inputs (daisyUI uses 0.1875–0.3125).",
    ),
    "border": ("--border", "px", 0, 4, "Border width", "Width of borders, in pixels."),
}
# name: (CSS variable, label, help)
EFFECTS = {
    "depth": ("--depth", "Depth", "A subtle 3D shadow on buttons and other controls."),
    "noise": ("--noise", "Noise", "A subtle grain texture on controls."),
}
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
