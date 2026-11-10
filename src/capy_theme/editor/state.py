"""What the editor panel receives: the draft's state and the controls it offers."""

from django.urls import reverse

from ..colors.names import COLOR_GROUPS, SCHEMES, label
from ..css.custom import without_custom_css
from ..css.shape import EFFECTS, SIZES
from ..css.stylesheet import snapshot_css
from ..css.typography import TYPE_SETTINGS
from ..fonts.library import ROLES, preview_stack
from ..fonts.models import Font
from ..images.icons import SETTINGS as ICON_SETTINGS
from ..images.logos import FALLBACK, HEIGHTS, LOGO_SLOTS
from ..images.slots import NO_SVG, SLOTS
from ..images.uploads import asset_data
from ..themes.catalogue import get_builtin_themes
from .access import can_publish
from .preview import preview
from .visitors import visitor_summary


def editor_urls(theme):
    return {
        "state": reverse("capy_theme:editor_state", args=[theme.pk]),
        "preview": reverse("capy_theme:editor_preview", args=[theme.pk]),
        "suggestions": reverse("capy_theme:editor_suggestions", args=[theme.pk]),
        "save": reverse("capy_theme:editor_save", args=[theme.pk]),
        "publish": reverse("capy_theme:editor_publish", args=[theme.pk]),
        "upload": reverse("capy_theme:editor_upload", args=[theme.pk]),
        "components": reverse("capy_theme:editor_components", args=[theme.pk]),
        "visitor_view": reverse("capy_theme:editor_visitor_view"),
    }


def draft_state(theme, user):
    """Everything the editor needs about a theme's draft, as JSON-ready data."""
    return {
        "id": theme.pk,
        "name": theme.name,
        "light_base": theme.light_base,
        "dark_base": theme.dark_base,
        "settings": without_custom_css(theme.settings),  # the editor doesn't edit it
        "css": snapshot_css(theme.snapshot(), f"capy-theme editor: draft of {theme.name}"),
        "live_revision": theme.live_revision.number if theme.live_revision else None,
        "has_unpublished_changes": theme.has_unpublished_changes,
        "can_publish": can_publish(user),
        "urls": editor_urls(theme),
        "assets": [asset_data(a) for a in theme.assets.all()],
        "controls": controls(),
        "visitors": visitor_summary(),
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
                "modes": ["light"] if slot == "social" else ["light", "dark"],
            }
            for slot in (*LOGO_SLOTS, "icon", "social", "background_login", "background_pattern")
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
