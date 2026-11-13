"""Which theme is active, cached so pages don't query the database each time.

The site's theme comes from its ThemeAssignment. With several sites (domains),
an assignment for the request's domain wins over the one for every site (blank
site); scheduled assignments work the same way per domain. A visitor can pick another
theme with {% theme_picker %}, but only one the operator offers (published, with
"Offer to visitors" ticked) and only if CAPY_THEME_VISITOR_THEMES is on.

The cache is cleared whenever a theme, revision or assignment changes (see
themes/signals.py). It also expires after CAPY_THEME_CACHE_SECONDS (default 300), so
every server process catches up even when the project's cache isn't shared
between processes.
"""

import logging
from uuid import uuid4

from django.core.cache import cache
from django.http.request import split_domain_port
from django.utils import timezone

from .. import conf
from ..models import Theme, ThemeAssignment

logger = logging.getLogger(__name__)

CACHE_KEY = "capy_theme:active_theme"
# Changed by clear_cache(), so every site's cached state is dropped at once.
GENERATION_KEY = "capy_theme:active_theme:generation"


class NotPublished(Exception):
    """Raised when activating a theme that has never been published."""


# The cookie holding a visitor's chosen theme (its slug).
CHOICE_COOKIE = "capy_theme_choice"


def get_active_theme(request=None):
    """Return the Theme to show (with its live revision loaded), or None.

    With a request, a visitor's choice from {% theme_picker %} wins if that theme
    is offered to visitors. Otherwise (or without a request) it's the site's theme.
    """
    state = _state(site_of(request))
    if request is not None and visitor_themes_allowed():
        chosen = state["offered"].get(request.COOKIES.get(CHOICE_COOKIE, ""))
        if chosen is not None:
            return chosen
    return state["theme"]


def get_site_theme(request=None):
    """The site's theme for the request's domain, without a visitor's own choice."""
    return _state(site_of(request))["theme"]


def offered_themes():
    """The published themes visitors may choose, by name."""
    return sorted(_state("")["offered"].values(), key=lambda theme: theme.name)


def site_of(request):
    """The request's domain, lower case and without the port ("" without a request)."""
    if request is None:
        return ""
    domain, _port = split_domain_port(request.get_host())
    return domain.lower()


def visitor_themes_allowed():
    """CAPY_THEME_VISITOR_THEMES: whether visitors may choose a theme (default True)."""
    return conf.get("CAPY_THEME_VISITOR_THEMES")


def _state(site):
    """The theme for `site` and the offered themes, from the cache or the database.

    A scheduled assignment (one with dates) wins while it's running; otherwise
    it's the default assignment. The site's own assignments win over the ones
    for every site. The cached state also expires at the next scheduled start or
    end, so a schedule is never missed.
    """
    now = timezone.now()
    key = f"{CACHE_KEY}:{_generation()}:{site or '*'}"
    cached = cache.get(key)
    if cached is not None and (cached["valid_until"] is None or now < cached["valid_until"]):
        return cached
    assignments = list(_assignments(site))
    current = _for_site(assignments, site, now)
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
    cache.set(key, state, timeout)
    return state


def _assignments(site):
    sites = [site, ""] if site else [""]
    return ThemeAssignment.objects.filter(site__in=sites).select_related("theme__live_revision")


def _for_site(assignments, site, when):
    """The site's own live assignment, else the one for every site."""
    if site:
        own = _current([a for a in assignments if a.site == site], when)
        if own is not None:
            return own
    return _current([a for a in assignments if a.site == ""], when)


def _current(assignments, when):
    """The assignment that's live at `when`: a running schedule, else the default.

    The most recently started schedule wins (e.g. a one-day sale inside a season).
    """
    running = [a for a in assignments if a.is_scheduled and a.is_running(when)]
    if running:
        return max(running, key=lambda a: (a.starts_at or a.created_at, a.created_at))
    return next((a for a in assignments if not a.is_scheduled), None)


def theme_at(when, site=""):
    """The site's theme at a given moment (not cached; for previews)."""
    current = _for_site(list(_assignments(site)), site, when)
    return current.theme if current else None


def scheduled_assignments(site=""):
    """The scheduled assignments (with a start or end date) for `site` and for every
    site, by start date."""
    sites = [site, ""] if site else [""]
    return list(
        ThemeAssignment.objects.filter(site__in=sites)
        .exclude(starts_at__isnull=True, ends_at__isnull=True)
        .select_related("theme")
        .order_by("starts_at", "ends_at")
    )


def activate(theme, site=""):
    """Make `theme` the active theme, for every site or for one domain.

    Raises NotPublished if it has no live revision.
    """
    if theme.live_revision_id is None:
        raise NotPublished(f"Publish “{theme}” before activating it.")
    ThemeAssignment.objects.update_or_create(
        site=site.lower(), starts_at=None, ends_at=None, defaults={"theme": theme}
    )
    clear_cache()
    logger.info("Activated theme %r for %s.", theme.slug, site.lower() or "every site")


def clear_cache():
    """Drop every site's cached state."""
    cache.set(GENERATION_KEY, uuid4().hex, None)


def _generation():
    generation = cache.get(GENERATION_KEY)
    if generation is None:  # first use, or evicted: start a fresh generation
        generation = uuid4().hex
        cache.set(GENERATION_KEY, generation, None)
    return generation


def cache_seconds():
    return conf.get("CAPY_THEME_CACHE_SECONDS")
