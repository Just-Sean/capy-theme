"""Which theme is active, cached so pages don't query the database each time.

The site's theme comes from its ThemeAssignment. A visitor can pick another
theme with {% theme_picker %}, but only one the operator offers (published, with
"Offer to visitors" ticked) and only if CAPY_THEME_VISITOR_THEMES is on.

The cache is cleared whenever a theme, revision or assignment changes (see
themes/signals.py). It also expires after CAPY_THEME_CACHE_SECONDS (default 300), so
every server process catches up even when the project's cache isn't shared
between processes.
"""

from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from ..models import Theme, ThemeAssignment

CACHE_KEY = "capy_theme:active_theme"


class NotPublished(Exception):
    """Raised when activating a theme that has never been published."""


# The cookie holding a visitor's chosen theme (its slug).
CHOICE_COOKIE = "capy_theme_choice"


def get_active_theme(request=None):
    """Return the Theme to show (with its live revision loaded), or None.

    With a request, a visitor's choice from {% theme_picker %} wins if that theme
    is offered to visitors. Otherwise (or without a request) it's the site's theme.
    """
    state = _state()
    if request is not None and visitor_themes_allowed():
        chosen = state["offered"].get(request.COOKIES.get(CHOICE_COOKIE, ""))
        if chosen is not None:
            return chosen
    return state["theme"]


def offered_themes():
    """The published themes visitors may choose, by name."""
    return sorted(_state()["offered"].values(), key=lambda theme: theme.name)


def visitor_themes_allowed():
    """CAPY_THEME_VISITOR_THEMES: whether visitors may choose a theme (default True)."""
    return getattr(settings, "CAPY_THEME_VISITOR_THEMES", True)


def _state():
    """The site's theme and the offered themes, from the cache or the database.

    A scheduled assignment (one with dates) wins while it's running; otherwise
    it's the default assignment. The cached state also expires at the next
    scheduled start or end, so a schedule is never missed.
    """
    now = timezone.now()
    cached = cache.get(CACHE_KEY)
    if cached is not None and (cached["valid_until"] is None or now < cached["valid_until"]):
        return cached
    assignments = ThemeAssignment.objects.filter(site="").select_related("theme__live_revision")
    running = [a for a in assignments if a.is_scheduled and a.is_running(now)]
    if running:
        # The most recently started schedule wins (e.g. a one-day sale inside a season).
        current = max(running, key=lambda a: (a.starts_at or a.created_at, a.created_at))
    else:
        current = next((a for a in assignments if not a.is_scheduled), None)
    boundaries = [
        moment
        for a in assignments
        for moment in (a.starts_at, a.ends_at)
        if moment is not None and moment > now
    ]
    valid_until = min(boundaries) if boundaries else None
    offered = Theme.objects.filter(
        offered_to_visitors=True, live_revision__isnull=False
    ).select_related("live_revision")
    state = {
        "theme": current.theme if current else None,
        "offered": {theme.slug: theme for theme in offered},
        "valid_until": valid_until,
    }
    timeout = cache_seconds()
    if valid_until is not None:
        timeout = max(1, min(timeout, int((valid_until - now).total_seconds()) + 1))
    # Stored in a dict so "no active theme" (None) is cached too.
    cache.set(CACHE_KEY, state, timeout)
    return state


def scheduled_assignments():
    """Every scheduled assignment (one with a start or end date), by start date."""
    return list(
        ThemeAssignment.objects.filter(site="")
        .exclude(starts_at__isnull=True, ends_at__isnull=True)
        .select_related("theme")
        .order_by("starts_at", "ends_at")
    )


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
