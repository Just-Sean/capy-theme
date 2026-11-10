"""Revision history: comparing two revisions and restoring an old one."""

from ..colors.names import COLOR_NAMES, label
from ..css.custom import summary as custom_css_summary
from ..css.shape import EFFECTS, SIZES
from ..images.slots import SLOTS
from .publishing import publish

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
    }
    for slot, modes in snapshot.get("images", {}).items():
        for mode, image in modes.items():
            rows[f"Image: {SLOTS.get(slot, (slot,))[0]} ({mode})"] = image["file"]
    if snapshot.get("logo"):
        rows["Image: Main logo (light)"] = snapshot["logo"]  # before logo slots
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
    # Custom CSS: whether it's on and its length, never its content.
    rows["Custom CSS"] = custom_css_summary(settings)
    known = set(SETTING_LABELS) | {"colors", "shape", "images", "custom_css"}
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
    _drop_deleted_images(theme)
    theme.save()
    return publish(theme, user=user, note=f"Restored revision {revision.number}")


def _drop_deleted_images(theme):
    """Forget chosen images that have since been deleted, so the restore still works."""
    chosen = theme.settings.get("images", {})
    existing = set(theme.assets.values_list("pk", flat=True))
    kept = {}
    for slot, modes in chosen.items():
        modes = {mode: pk for mode, pk in modes.items() if pk in existing}
        if modes:
            kept[slot] = modes
    if kept:
        theme.settings["images"] = kept
    else:
        theme.settings.pop("images", None)
