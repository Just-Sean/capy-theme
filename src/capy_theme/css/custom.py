"""Custom CSS: an escape hatch for anything the theme settings don't cover.

Saved with the theme (settings["custom_css"] = {"css": "...", "enabled": true}),
so it's drafted and published like everything else. Each published revision's
custom CSS is served as its own file after the theme stylesheet. Only users with
the edit_custom_css permission can see or change it.
"""

from django.urls import reverse

MAX_LENGTH = 100_000  # characters (also in settings.schema.json)
PERMISSION = "capy_theme.edit_custom_css"


def custom_css(snapshot):
    """The revision's custom CSS if it's switched on and not empty, else ""."""
    chosen = snapshot.get("settings", {}).get("custom_css", {})
    if not chosen.get("enabled", True):
        return ""
    return chosen.get("css", "").strip()


def custom_css_url(revision):
    """The address of the revision's custom CSS file, or None if it has none."""
    if not custom_css(revision.snapshot):
        return None
    return reverse("capy_theme:custom_css", args=[revision.css_version])


def can_edit_custom_css(user):
    return bool(user and user.has_perm(PERMISSION))


def summary(settings):
    """A description of the custom CSS without its content, e.g. "on, 120 characters"."""
    chosen = settings.get("custom_css")
    if not chosen:
        return None
    state = "on" if chosen.get("enabled", True) else "off"
    return f"{state}, {len(chosen.get('css', ''))} characters"


def without_custom_css(settings):
    """`settings` without the custom CSS, for places that mustn't show it."""
    return {key: value for key, value in settings.items() if key != "custom_css"}
