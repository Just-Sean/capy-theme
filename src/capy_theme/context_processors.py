"""Gives every template a `theme` variable describing the active theme.

Add "capy_theme.context_processors.theme" to the project's
TEMPLATES["OPTIONS"]["context_processors"].
"""

from .colors.maths import hex_colors
from .colors.values import effective_values
from .css.backgrounds import template_values as background_urls
from .css.stylesheet import stylesheet_url
from .themes.active import get_active_theme
from .themes.branding import branding
from .themes.mode import current_mode, mode_settings


def theme(request):
    """Return {"theme": ...}: the active theme's published values, or None.

    The values come from the live revision, not the draft, so templates show
    what's published. Later phases add more (colours, fonts and so on).
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
            "stylesheet_url": stylesheet_url(live),
            **branding(live),  # site_name, tagline, logo_url, logo_alt
            # background_login_url and background_pattern_url ("" if not set)
            **background_urls(live.snapshot),
            "default_mode": mode_settings(live)[0],
            "visitors_can_switch": mode_settings(live)[1],
            "mode": current_mode(request, live),  # what this visitor sees
            # Light-mode colours as #rrggbb for HTML emails, e.g. theme.email_colors.primary.
            "email_colors": hex_colors(effective_values(live.snapshot, "light")),
        }
    }
