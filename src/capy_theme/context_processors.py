"""Gives every template a `theme` variable describing the active theme.

Add "capy_theme.context_processors.theme" to the project's
TEMPLATES["OPTIONS"]["context_processors"].
"""

from django.urls import reverse

from .active import get_active_theme


def theme(request):
    """Return {"theme": ...}: the active theme's published values, or None.

    The values come from the live revision, not the draft, so templates show
    what's published. Later phases add more (site name, logo and so on).
    """
    active = get_active_theme(request)
    if active is None or active.live_revision is None:
        return {"theme": None}
    live = active.live_revision
    return {
        "theme": {
            "name": active.name,
            "slug": active.slug,
            "revision": live.number,
            "light_base": live.snapshot["light_base"],
            "dark_base": live.snapshot["dark_base"],
            "stylesheet_url": reverse("capy_theme:theme_css", args=[live.css_version]),
        }
    }
