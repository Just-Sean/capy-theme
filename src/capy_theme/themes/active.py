"""The domain's default themes, cached so pages don't query the database each time.

A theme is a single scheme (light or dark), so a domain has up to two defaults: a
default light theme and a default dark theme. A consumer switches between them (its
own light/dark toggle). Each comes from a ThemeAssignment for that scheme: with
several sites (domains), an assignment for the request's domain wins over the one
for every site (blank site); scheduled assignments work the same way per domain.
capy-theme no longer tracks a per-visitor choice — a consumer picks a theme from
the catalog and fetches its assets.

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
from django.utils import timezone

from .. import conf
from ..models import Theme, ThemeAssignment

logger = logging.getLogger(__name__)

SCHEMES = ("light", "dark")

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


def default_themes(request=None):
    """The domain's default themes: ``{"light": theme or None, "dark": theme or None}``.

    Each is the admin's default (or scheduled) theme for that scheme on the request's
    domain, with its live revision loaded. capy-theme doesn't track a per-visitor
    choice — a consumer picks a theme itself from the catalog and fetches its assets.
    """
    return _state(site_of(request))["themes"]


def primary_theme(request=None):
    """The domain's primary theme — its default light theme, or its default dark
    theme if no light default is set, or None. For a single-theme consumer such as
    an email or a PWA manifest (see artifacts.get_artifacts)."""
    themes = default_themes(request)
    return themes["light"] or themes["dark"]


def offered_themes():
    """The published themes offered to visitors, by name (for the catalog)."""
    return sorted(_state("")["offered"].values(), key=lambda theme: theme.name)


def catalog_theme(slug, request=None):
    """A published theme a consumer may fetch by slug for this request, or None.

    ``slug`` is a theme offered to visitors, or ``"default"`` / its own slug for one
    of the **domain's** default themes. Only those are reachable, so an unpublished or
    not-offered theme can't be fetched. ``"default"`` gives the domain's primary theme.
    """
    defaults = default_themes(request)
    if slug == "default":
        return defaults["light"] or defaults["dark"]
    offered = {theme.slug: theme for theme in offered_themes()}
    if slug in offered:
        return offered[slug]
    for theme in defaults.values():
        if theme is not None and theme.slug == slug:
            return theme
    return None


def site_of(request):
    """The request's domain, lower case and without the port ("" without a request)."""
    if request is None:
        return ""
    domain, _port = split_domain_port(request.get_host())
    return domain.lower()


def _state(site):
    """The default themes for `site` and the offered themes, from the cache or database.

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
        and "themes" in cached
        and (cached["valid_until"] is None or now < cached["valid_until"])
    ):
        return cached
    try:
        state, timeout = _state_from_db(site, now)
    except DatabaseError:
        logger.exception("capy-theme: could not load the active theme; serving no theme")
        return {"themes": {"light": None, "dark": None}, "offered": {}, "valid_until": None}
    _cache_set(key, state, timeout)
    return state


def _state_from_db(site, now):
    """Build `site`'s state from the database, with the cache timeout to store it for."""
    assignments = list(_assignments(site))
    themes = {}
    for scheme in SCHEMES:
        current = _for_site([a for a in assignments if a.scheme == scheme], site, now)
        themes[scheme] = current.theme if current else None
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
        "themes": themes,
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
    """The site's own live assignment, else the one for every site (for one scheme)."""
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


def theme_at(when, scheme, site=""):
    """The site's theme for one scheme at a given moment (not cached; for previews)."""
    assignments = [a for a in _assignments(site) if a.scheme == scheme]
    current = _for_site(assignments, site, when)
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


def default_theme(scheme, site=""):
    """The default theme for one scheme on `site` (the undated assignment), or None.
    Read from the database."""
    assignment = (
        ThemeAssignment.objects.select_related("theme")
        .filter(site=site.lower(), scheme=scheme, starts_at=None, ends_at=None)
        .first()
    )
    return assignment.theme if assignment else None


def activate(theme, site=""):
    """Make `theme` the default theme for its scheme, for every site or one domain.

    The scheme comes from the theme (a light theme becomes the light default, a
    dark theme the dark default). Raises NotPublished if it has no live revision.
    """
    if theme.live_revision_id is None:
        raise NotPublished(not_published_message(theme))
    ThemeAssignment.objects.update_or_create(
        site=site.lower(),
        scheme=theme.scheme,
        starts_at=None,
        ends_at=None,
        defaults={"theme": theme},
    )
    clear_cache()
    logger.info(
        "Activated theme %r as the %s default for %s.",
        theme.slug,
        theme.scheme,
        site.lower() or "every site",
    )


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
