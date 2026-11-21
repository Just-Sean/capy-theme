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
import time
from uuid import uuid4

from django.core.cache import cache
from django.db import Error as DatabaseError
from django.http.request import split_domain_port
from django.urls import reverse
from django.utils import timezone
from django.utils.http import urlencode

from .. import conf
from ..models import Theme, ThemeAssignment

logger = logging.getLogger(__name__)

CACHE_KEY = "capy_theme:active_theme"
# Changed by clear_cache(), so every site's cached state is dropped at once.
GENERATION_KEY = "capy_theme:active_theme:generation"

# A cache-backend outage is logged at most this often (seconds), so a sustained
# outage under traffic can't flood the log with one line per cache operation.
_CACHE_OUTAGE_LOG_INTERVAL = 60
_last_cache_outage_log = 0.0


def _log_cache_outage(exc):
    """Log a cache-backend failure at WARNING, throttled and without a traceback.

    The active-theme path falls back to the database, so a cache outage isn't an
    error; it's logged so it stays visible, but at most once per interval and
    without a full traceback, so it can't amplify the outage it's surviving.
    """
    global _last_cache_outage_log
    now = time.monotonic()
    if now - _last_cache_outage_log >= _CACHE_OUTAGE_LOG_INTERVAL:
        _last_cache_outage_log = now
        logger.warning("capy-theme: cache unavailable (%s); serving from the database", exc)


def _cache_get(key):
    """cache.get(key), or None if the cache backend can't be reached.

    A cache outage (e.g. Redis down) must not take a page down: the caller falls
    back to the database. The outage is logged (throttled) so it stays visible.
    """
    try:
        return cache.get(key)
    except Exception as exc:
        _log_cache_outage(exc)
        return None


def _cache_set(key, value, timeout):
    """cache.set(...), skipped if the cache backend can't be reached (logged, throttled)."""
    try:
        cache.set(key, value, timeout)
    except Exception as exc:
        _log_cache_outage(exc)


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


def picker_state(request):
    """The themes a visitor may choose, as plain data for a consumer to render its own
    picker. Returns {"allowed", "current", "options"}; each option is
    {"value", "label", "url", "current"}, where "default" is the site's own theme and
    "url" sets the choice and returns to the current page (so a plain link works without
    JavaScript). "allowed" is False (and only "Site default" is offered) when
    CAPY_THEME_VISITOR_THEMES is off. See docs/artifacts.md.
    """
    allowed = visitor_themes_allowed()
    back = request.get_full_path() if request is not None else "/"
    offered = offered_themes() if allowed else []
    chosen = request.COOKIES.get(CHOICE_COOKIE, "") if request is not None else ""
    if chosen not in {theme.slug for theme in offered}:
        chosen = "default"

    def choose_url(slug):
        return reverse("capy_theme:choose_theme", args=[slug]) + "?" + urlencode({"next": back})

    options = [
        {
            "value": "default",
            "label": "Site default",
            "url": choose_url("default"),
            "current": chosen == "default",
        }
    ]
    options += [
        {"value": t.slug, "label": t.name, "url": choose_url(t.slug), "current": chosen == t.slug}
        for t in offered
    ]
    return {"allowed": allowed, "current": chosen, "options": options}


def _state(site):
    """The theme for `site` and the offered themes, from the cache or the database.

    A scheduled assignment (one with dates) wins while it's running; otherwise
    it's the default assignment. The site's own assignments win over the ones
    for every site. The cached state also expires at the next scheduled start or
    end, so a schedule is never missed.

    Resilient to outages (issue #278): a cache failure falls back to the
    database, and a database failure falls back to "no theme", so a page — even
    the 500 page — renders unthemed instead of raising.
    """
    now = timezone.now()
    key = f"{CACHE_KEY}:{_generation()}:{site or '*'}"
    cached = _cache_get(key)
    # A malformed or old-shape cached value (e.g. a cache shared across deployments
    # or versions) is treated as a miss, so it can't 500 the page (#282).
    if (
        isinstance(cached, dict)
        and "valid_until" in cached
        and (cached["valid_until"] is None or now < cached["valid_until"])
    ):
        return cached
    try:
        state, timeout = _state_from_db(site, now)
    except DatabaseError:
        logger.exception("capy-theme: could not load the active theme; serving no theme")
        return {"theme": None, "offered": {}, "valid_until": None}
    # Stored in a dict so "no active theme" (None) is cached too.
    _cache_set(key, state, timeout)
    return state


def _state_from_db(site, now):
    """Build `site`'s state from the database, with the cache timeout to store it for."""
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
    return state, timeout


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


def not_published_message(theme):
    """What to tell someone who tries to activate a theme that's never been published.
    Built here, not read back from the exception, so nothing else can leak into it."""
    return f"Publish “{theme}” before activating it."


def default_theme():
    """The theme activated for every site (the default when no schedule is running
    and a domain has no site theme of its own), or None. Read from the database."""
    assignment = (
        ThemeAssignment.objects.select_related("theme")
        .filter(site="", starts_at=None, ends_at=None)
        .first()
    )
    return assignment.theme if assignment else None


def activate(theme, site=""):
    """Make `theme` the active theme, for every site or for one domain.

    Raises NotPublished if it has no live revision.
    """
    if theme.live_revision_id is None:
        raise NotPublished(not_published_message(theme))
    ThemeAssignment.objects.update_or_create(
        site=site.lower(), starts_at=None, ends_at=None, defaults={"theme": theme}
    )
    clear_cache()
    logger.info("Activated theme %r for %s.", theme.slug, site.lower() or "every site")


def clear_cache():
    """Drop every site's cached state (a no-op if the cache is unreachable)."""
    _cache_set(GENERATION_KEY, uuid4().hex, None)


def _generation():
    generation = _cache_get(GENERATION_KEY)
    if generation is None:  # first use, evicted, or cache down: start a fresh generation
        generation = uuid4().hex
        _cache_set(GENERATION_KEY, generation, None)
    return generation


def cache_seconds():
    return conf.get("CAPY_THEME_CACHE_SECONDS")
