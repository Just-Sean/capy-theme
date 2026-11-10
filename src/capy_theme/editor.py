"""The live theme editor: who can use it, which theme it edits, and its data.

The editor is a panel on top of a real page. It previews a theme's draft in
that browser only (visitors keep seeing the published theme) and talks to the
JSON views in views.py, which use the same code as publishing.
"""

import copy

from django.core.exceptions import ValidationError
from django.urls import reverse

from .active import get_active_theme
from .colors import SCHEMES, contrast_report, effective_values, to_oklch
from .models import Theme
from .stylesheet import snapshot_css
from .validation import validate_base, validate_settings


def can_edit(user):
    """Staff who can change themes can open the editor."""
    return bool(
        user.is_authenticated
        and user.is_active
        and user.is_staff
        and user.has_perm("capy_theme.change_theme")
    )


def can_publish(user):
    return can_edit(user) and user.has_perm("capy_theme.publish_theme")


def editor_theme(request):
    """The theme the editor works on: ?edit=<id> if given, else the active theme."""
    requested = request.GET.get("edit", "")
    if requested.isdigit():
        return Theme.objects.filter(pk=int(requested)).first()
    active = get_active_theme(request)
    return Theme.objects.filter(pk=active.pk).first() if active else None


def editor_urls(theme):
    return {
        "state": reverse("capy_theme:editor_state", args=[theme.pk]),
        "preview": reverse("capy_theme:editor_preview", args=[theme.pk]),
    }


def draft_state(theme, user):
    """Everything the editor needs about a theme's draft, as JSON-ready data."""
    return {
        "id": theme.pk,
        "name": theme.name,
        "light_base": theme.light_base,
        "dark_base": theme.dark_base,
        "settings": theme.settings,
        "css": snapshot_css(theme.snapshot(), f"capy-theme editor: draft of {theme.name}"),
        "live_revision": theme.live_revision.number if theme.live_revision else None,
        "has_unpublished_changes": theme.has_unpublished_changes,
        "can_publish": can_publish(user),
        "urls": editor_urls(theme),
    }


# The settings the editor manages. Anything else in a theme's settings (site
# name, mode and so on) is kept as it is.
EDITOR_SETTINGS = ("colors", "shape")


def apply_changes(theme, data):
    """Return an unsaved copy of `theme` with the editor's values applied.

    `data` may have "light_base", "dark_base" and "settings" (with "colors" and
    "shape"). Colours can be in any CSS format; they're converted to OKLCH.
    Raises ValidationError (with every problem) if anything is invalid.
    The theme itself and the database are never changed.
    """
    draft = copy.copy(theme)
    errors = []
    for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
        if field in data:
            setattr(draft, field, str(data[field]))
            try:
                validate_base(getattr(draft, field), scheme)
            except ValidationError as error:
                errors.extend(error.messages)
    settings = copy.deepcopy(theme.settings)
    changes = data.get("settings", {})
    if not isinstance(changes, dict):
        raise ValidationError("settings must be an object.")
    for key in EDITOR_SETTINGS:
        if key in changes:
            if changes[key]:
                settings[key] = changes[key]
            else:
                settings.pop(key, None)
    for scheme, colors in settings.get("colors", {}).items():
        if not isinstance(colors, dict):
            continue
        for name, value in colors.items():
            try:
                colors[name] = to_oklch(str(value))
            except ValueError:
                errors.append(f"{scheme} {name}: {value!r} isn't a colour.")
    if not errors:
        try:
            validate_settings(settings)
        except ValidationError as error:
            errors.extend(error.messages)
    if errors:
        raise ValidationError(errors)
    draft.settings = settings
    return draft


def preview(theme, data):
    """Return what the editor shows for unsaved values: CSS, values and contrast.

    Uses the same code as publishing, so the preview matches what would be
    published. Writes nothing.
    """
    draft = apply_changes(theme, data)
    snapshot = draft.snapshot()
    values = {scheme: effective_values(snapshot, scheme) for scheme in SCHEMES}
    return {
        "css": snapshot_css(snapshot, f"capy-theme editor: preview of {theme.name}"),
        "values": values,
        "contrast": {scheme: contrast_report(values[scheme]) for scheme in SCHEMES},
        "settings": draft.settings,
    }
