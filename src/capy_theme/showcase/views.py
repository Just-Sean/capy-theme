"""The theme showcase page."""

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from ..editor.access import can_edit, editor_theme
from ..themes.active import (
    get_active_theme,
    offered_themes,
    scheduled_assignments,
    visitor_themes_allowed,
)
from ..themes.branding import branding
from ..themes.mode import (
    MODE_LABELS,
    current_mode,
    mode_settings,
)
from .colors_shape import shape_samples, swatches
from .images import images as showcase_images
from .typography import typography

# The showcase page. Each section is its own template in
# templates/capy_theme/showcase/sections/, shown once per mode. Later phases add
# their sections by adding a template and a name here.
SHOWCASE_SECTIONS = [
    "branding",
    "images",
    "colors",
    "shape",
    "fonts",
    "typography",
    "buttons",
    "badges",
    "alerts",
    "cards",
    "tabs",
    "table",
    "forms",
    "progress",
    "modal",
]


SHOWCASE_ACCESS = ("staff", "public", "off")


def showcase(request):
    """Show the active theme's choices on every kind of component, in light and dark."""
    access = getattr(settings, "CAPY_THEME_SHOWCASE", "staff")
    if access not in SHOWCASE_ACCESS:
        raise ImproperlyConfigured(
            f"CAPY_THEME_SHOWCASE must be one of {', '.join(SHOWCASE_ACCESS)}, not {access!r}."
        )
    if access == "off":
        raise Http404("The theme showcase is turned off.")
    if access == "staff" and not (request.user.is_active and request.user.is_staff):
        return redirect_to_login(request.get_full_path(), reverse("admin:login"))

    theme = get_active_theme(request)
    revision = theme.live_revision if theme else None
    context = {
        "base_template": getattr(
            settings, "CAPY_THEME_BASE_TEMPLATE", "capy_theme/showcase/standalone.html"
        ),
        "active_theme": theme,
        "revision": revision,
        "brand": branding(revision) if revision else {},
        "modes": ["light", "dark"],
        "sections": [f"capy_theme/showcase/sections/{name}.html" for name in SHOWCASE_SECTIONS],
        "swatches": swatches(revision),
        "shape_samples": shape_samples(revision),
        "type_samples": typography(revision),
        "image_samples": showcase_images(revision),
        "visitors": _visitor_context(request, revision),
        "editor": _editor_context(request),
    }
    return render(request, "capy_theme/showcase/page.html", context)


def _visitor_context(request, revision):
    """The showcase's "Mode and visitors" panel: settings, offered and scheduled themes."""
    default_mode, can_switch = mode_settings(revision) if revision else ("auto", True)
    now = timezone.now()
    return {
        "default_mode": MODE_LABELS[default_mode],
        "can_switch": can_switch,
        "current_mode": MODE_LABELS[current_mode(request, revision)] if revision else "Auto",
        "picker_on": visitor_themes_allowed(),
        "offered": offered_themes(),
        "schedule": [
            {
                "theme": a.theme.name,
                "starts_at": a.starts_at,
                "ends_at": a.ends_at,
                "running": a.is_running(now),
            }
            for a in scheduled_assignments()
            if a.ends_at is None or a.ends_at > now
        ],
    }


def _editor_context(request):
    """Whether to show the showcase's Edit theme button (the editor itself comes
    from {% theme_head %})."""
    if not can_edit(request.user):
        return None
    theme = editor_theme(request)
    if theme is None:
        return None
    return {"theme": theme}
