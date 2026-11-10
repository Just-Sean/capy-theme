"""Revision history: comparing two revisions and restoring an old one."""

from .colors import COLOR_NAMES, label
from .publishing import publish
from .shape import EFFECTS, SIZES

SETTING_LABELS = {
    "site_name": "Site name",
    "tagline": "Tagline",
    "logo_alt": "Logo alt text",
    "default_mode": "Default mode",
    "visitors_can_switch": "Visitors can switch",
}


def describe(snapshot):
    """Return {readable name: value} for everything a revision saved.

    E.g. {"Light base": "cupcake", "Light colour: Primary": "oklch(...)",
    "Shape: Box corner radius": 0.0}. Used to compare revisions.
    """
    settings = snapshot.get("settings", {})
    rows = {
        "Light base": snapshot.get("light_base"),
        "Dark base": snapshot.get("dark_base"),
        "Logo": snapshot.get("logo") or None,
    }
    for key, title in SETTING_LABELS.items():
        rows[title] = settings.get(key)
    for scheme in ("light", "dark"):
        chosen = settings.get("colors", {}).get(scheme, {})
        for name in COLOR_NAMES:
            rows[f"{scheme.capitalize()} colour: {label(name)}"] = chosen.get(name)
    shape = settings.get("shape", {})
    for name, spec in SIZES.items():
        rows[f"Shape: {spec[4]}"] = shape.get(name)
    for name, spec in EFFECTS.items():
        rows[f"Shape: {spec[1]}"] = shape.get(name)
    known = set(SETTING_LABELS) | {"colors", "shape"}
    for key, value in settings.items():
        if key not in known:
            rows[key] = value  # settings added by later versions
    return rows


def compare(older, newer):
    """Return the rows that differ between two revisions: [{name, older, newer}].

    Values that weren't set (base theme used) are shown as None.
    """
    a, b = describe(older.snapshot), describe(newer.snapshot)
    return [
        {"name": name, "older": a.get(name), "newer": b.get(name)}
        for name in dict.fromkeys([*a, *b])
        if a.get(name) != b.get(name)
    ]


def restore(theme, revision, user=None):
    """Make an old revision live again, as a new revision. Returns the new revision.

    The revision's base themes, logo and settings are copied into the theme's
    draft and published. The history isn't rewritten: the old revision stays,
    and a new one (with a note saying what was restored) becomes live. Raises
    NothingToPublish if the live revision already matches.
    """
    snapshot = revision.snapshot
    theme.light_base = snapshot["light_base"]
    theme.dark_base = snapshot["dark_base"]
    theme.settings = dict(snapshot.get("settings", {}))
    theme.logo.name = snapshot.get("logo") or ""
    theme.save()
    return publish(theme, user=user, note=f"Restored revision {revision.number}")
