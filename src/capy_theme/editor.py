"""The live theme editor: who can use it, which theme it edits, and its data.

The editor is a panel on top of a real page. It previews a theme's draft in
that browser only (visitors keep seeing the published theme) and talks to the
JSON views in views.py, which use the same code as publishing.
"""

from django.urls import reverse

from .active import get_active_theme
from .models import Theme
from .stylesheet import snapshot_css


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
    return {"state": reverse("capy_theme:editor_state", args=[theme.pk])}


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
