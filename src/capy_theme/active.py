"""Which theme is active, cached so pages don't query the database each time.

The cache is cleared whenever a theme, revision or assignment changes (see
signals.py). It also expires after CAPY_THEME_CACHE_SECONDS (default 300), so
every server process catches up even when the project's cache isn't shared
between processes.
"""

from django.conf import settings
from django.core.cache import cache

from .models import ThemeAssignment

CACHE_KEY = "capy_theme:active_theme"


class NotPublished(Exception):
    """Raised when activating a theme that has never been published."""


def get_active_theme(request=None):
    """Return the active Theme (with its live revision loaded), or None.

    `request` isn't used yet; multiple sites (8.2) and draft previews (5.3)
    will use it.
    """
    cached = cache.get(CACHE_KEY)
    if cached is not None:
        return cached["theme"]

    assignment = (
        ThemeAssignment.objects.filter(site="", starts_at__isnull=True, ends_at__isnull=True)
        .select_related("theme__live_revision")
        .first()
    )
    theme = assignment.theme if assignment else None
    # Stored in a dict so "no active theme" (None) is cached too.
    cache.set(CACHE_KEY, {"theme": theme}, cache_seconds())
    return theme


def activate(theme):
    """Make `theme` the active theme. Raises NotPublished if it has no live revision."""
    if theme.live_revision_id is None:
        raise NotPublished(f"Publish “{theme}” before activating it.")
    ThemeAssignment.objects.update_or_create(
        site="", starts_at=None, ends_at=None, defaults={"theme": theme}
    )
    clear_cache()


def clear_cache():
    cache.delete(CACHE_KEY)


def cache_seconds():
    return getattr(settings, "CAPY_THEME_CACHE_SECONDS", 300)
