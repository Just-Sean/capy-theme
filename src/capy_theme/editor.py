"""The live theme editor: who can use it, which theme it edits, and its data.

The editor is a panel on top of a real page. It previews a theme's draft in
that browser only (visitors keep seeing the published theme) and talks to the
JSON views in views.py, which use the same code as publishing.
"""

import copy

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.urls import reverse

from .active import get_active_theme
from .catalogue import get_builtin_themes
from .colors import (
    COLOR_GROUPS,
    SCHEMES,
    contrast_report,
    effective_values,
    label,
    to_hex,
    to_oklch,
)
from .fonts import ROLES, external_stylesheets, preview_stack
from .icons import SETTINGS as ICON_SETTINGS
from .images import NO_SVG, SLOTS, asset_data
from .logos import FALLBACK, HEIGHTS, LOGO_SLOTS
from .models import Font, Theme
from .palette import from_logo, from_primary
from .shape import EFFECTS, SIZES
from .stylesheet import snapshot_css
from .typography import TYPE_SETTINGS
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
        "suggestions": reverse("capy_theme:editor_suggestions", args=[theme.pk]),
        "save": reverse("capy_theme:editor_save", args=[theme.pk]),
        "publish": reverse("capy_theme:editor_publish", args=[theme.pk]),
        "upload": reverse("capy_theme:editor_upload", args=[theme.pk]),
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
        "assets": [asset_data(a) for a in theme.assets.all()],
        "controls": controls(),
        **preview(theme, {}),
    }


def controls():
    """What the editor panel offers: bases, colour groups and shape settings."""
    return {
        "bases": {
            scheme: [t.name for t in get_builtin_themes() if t.scheme == scheme]
            for scheme in SCHEMES
        },
        "color_groups": [
            {"name": group, "colors": [{"name": n, "label": label(n)} for n in names]}
            for group, names in COLOR_GROUPS.items()
        ],
        "sizes": [
            {"name": name, "variable": v, "unit": unit, "min": low, "max": high, "label": lab}
            for name, (v, unit, low, high, lab, _help) in SIZES.items()
        ],
        "effects": [
            {"name": name, "variable": v, "label": lab} for name, (v, lab, _help) in EFFECTS.items()
        ],
        "image_slots": [
            {
                "name": name,
                "label": lab,
                "max_bytes": max_bytes,
                "max_pixels": px,
                "help": text,
                "svg": name not in NO_SVG,
            }
            for name, (lab, max_bytes, px, text) in SLOTS.items()
        ],
        "logo_slots": [
            {
                "name": slot,
                "label": SLOTS[slot][0],
                "fallback": "Use the main logo" if slot in FALLBACK else "None",
            }
            for slot in (*LOGO_SLOTS, "icon")
        ],
        "icon_settings": [
            {"name": name, "label": lab, "help": text}
            for name, (lab, text) in ICON_SETTINGS.items()
        ],
        "logo_heights": [
            {"name": name, "label": lab, "default": default}
            for name, (lab, default) in HEIGHTS.items()
        ],
        "font_roles": [{"name": name, "label": lab} for name, lab in ROLES.items()],
        "type": [
            {"name": name, "label": lab, "unit": unit, "min": low, "max": high, "step": step}
            for name, (lab, unit, low, high, step, _help) in TYPE_SETTINGS.items()
        ],
        "fonts": [
            {
                "id": f.pk,
                "family": f.family,
                "source": f.get_source_display(),
                "stack": preview_stack(f),
            }
            for f in Font.objects.all()
        ],
    }


# The settings the editor manages. Anything else in a theme's settings (site
# name, mode and so on) is kept as it is.
EDITOR_SETTINGS = ("colors", "shape", "fonts", "type", "images", "logo", "icon")


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
    if not errors:
        draft.settings = settings
        try:
            draft.clean()  # e.g. fonts that aren't in the library
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
        # Hex for the browser's colour pickers, keyed like "primary" or "base-100".
        "hex": {
            scheme: {
                key.removeprefix("--color-"): to_hex(value, alpha=False)
                for key, value in values[scheme].items()
                if key.startswith("--color-")
            }
            for scheme in SCHEMES
        },
        "contrast": {scheme: contrast_report(values[scheme]) for scheme in SCHEMES},
        "settings": draft.settings,
        "light_base": draft.light_base,
        "dark_base": draft.dark_base,
        # External font stylesheets (e.g. Adobe Fonts) the page must link.
        "stylesheets": external_stylesheets(snapshot.get("fonts")),
    }


def main_logo_asset(theme):
    """The draft's main logo (light), if it's a raster image; else None."""
    pk = theme.settings.get("images", {}).get("logo_main", {}).get("light")
    asset = theme.assets.filter(pk=pk).first() if pk else None
    return asset if asset and asset.content_type != "image/svg+xml" else None


def suggestions(theme, primary):
    """Palette suggestions for the editor: from `primary`, and from the theme's logo."""
    result = []
    logo = main_logo_asset(theme)
    if logo:
        with logo.original.open("rb") as file:
            suggestion = from_logo(file)
        if suggestion:
            result.append(suggestion)
    if primary:
        result.extend(from_primary(primary))
    return result


def save_draft(theme, data):
    """Store the editor's values in the theme's draft. Visitors see nothing until publish.

    Validated exactly like the preview. Only the bases, colours and shape are
    changed; the rest of the theme (name, branding, mode) is left as it is.
    """
    draft = apply_changes(theme, data)
    theme.light_base = draft.light_base
    theme.dark_base = draft.dark_base
    theme.settings = draft.settings
    theme.save()
    return theme


def mount(request):
    """The editor's <head> tags for this request, or "" if this user can't edit.

    Output by {% theme_head %}, so the editor works on every page that uses it.
    """
    user = getattr(request, "user", None)  # absent without Django's auth middleware
    if user is None or not can_edit(user):
        return ""
    theme = editor_theme(request)
    if theme is None:
        return ""
    context = {
        "editor": {
            "theme": theme,
            "urls": editor_urls(theme),
            "floating_button": getattr(django_settings, "CAPY_THEME_EDITOR_BUTTON", True),
        }
    }
    return render_to_string("capy_theme/editor/mount.html", context, request=request)
