"""The JSON API: the active theme's artifacts at /theme/api.json.

Front ends, mobile apps and other modules read it. It's the same data as
get_artifacts(), with absolute URLs. Responses carry an ETag, so a client that
sends it back (If-None-Match) gets "304 Not Modified" until the theme changes.

Two ways to serve it, chosen by CAPY_THEME_API:
- "auto" (default): the DRF view if Django REST Framework is installed, so
  drf-spectacular lists it in the project's API docs; otherwise the plain view.
- "drf": always the DRF view (the project must have DRF installed).
- "django": always the plain Django view.
Both return the same JSON.
"""

import hashlib
import json

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseNotModified, JsonResponse
from django.utils.cache import patch_vary_headers
from django.views.decorators.http import require_GET

from .. import conf
from ..themes.active import catalog_theme
from .build import build_artifacts, get_artifacts, theme_catalog

API_MODES = ("auto", "drf", "django")
CACHE_CONTROL = "public, max-age=60"  # short: the address stays the same after publishing


def _etag(data):
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return '"' + hashlib.sha256(canonical).hexdigest()[:32] + '"'


def payload(request):
    """(data, ETag) for the API, or (None, None) if no theme is published."""
    data = get_artifacts(request)
    if data is None:
        return None, None
    return data, _etag(data)


def catalog_payload(request):
    """(catalog list, ETag) — never None; an empty catalog is []."""
    data = theme_catalog(request)
    return data, _etag(data)


def theme_payload(request, slug):
    """(a theme's assets, ETag), or (None, None) if there's no such published theme."""
    theme = catalog_theme(slug)
    if theme is None or theme.live_revision is None:
        return None, None
    data = build_artifacts(theme, request)
    return data, _etag(data)


def cache_publicly(response):
    """Let browsers and shared caches keep the response for a minute.

    The content depends on the visitor's theme choice (a cookie), so caches must
    keep one copy per cookie (Vary: Cookie), or one visitor's choice would be
    served to everyone.
    """
    response["Cache-Control"] = CACHE_CONTROL
    patch_vary_headers(response, ["Cookie"])
    return response


def cache_static(response):
    """Public caching for the catalog and per-theme endpoints.

    These are keyed by slug, not by a visitor cookie, so there's no Vary: Cookie.
    """
    response["Cache-Control"] = CACHE_CONTROL
    return response


def not_modified(request, etag):
    """True if the client already has this version (its If-None-Match matches)."""
    sent = request.headers.get("If-None-Match", "")
    return etag in [tag.strip() for tag in sent.split(",")] or sent.strip() == "*"


@require_GET
def theme_api(request):
    """The plain Django view of the API."""
    data, etag = payload(request)
    if data is None:
        return JsonResponse({"error": "No theme is published."}, status=404)
    if not_modified(request, etag):
        response = HttpResponseNotModified()
    else:
        response = JsonResponse(data)
    response["ETag"] = etag
    return cache_publicly(response)


@require_GET
def theme_catalog_api(request):
    """The plain Django view of the themes catalog (/theme/themes.json)."""
    data, etag = catalog_payload(request)
    if not_modified(request, etag):
        response = HttpResponseNotModified()
    else:
        response = JsonResponse(data, safe=False)  # a list
    response["ETag"] = etag
    return cache_static(response)


@require_GET
def theme_assets_api(request, slug):
    """The plain Django view of one theme's assets (/theme/themes/<slug>.json)."""
    data, etag = theme_payload(request, slug)
    if data is None:
        return JsonResponse({"error": "No such theme."}, status=404)
    if not_modified(request, etag):
        response = HttpResponseNotModified()
    else:
        response = JsonResponse(data)
    response["ETag"] = etag
    return cache_static(response)


def api_mode():
    """ "drf" or "django": which view serves the API in this project."""
    mode = conf.get("CAPY_THEME_API")
    if mode not in API_MODES:
        raise ImproperlyConfigured(
            f"CAPY_THEME_API must be one of {', '.join(API_MODES)}, not {mode!r}."
        )
    drf = apps.is_installed("rest_framework")
    if mode == "drf" and not drf:
        raise ImproperlyConfigured(
            'CAPY_THEME_API = "drf" needs Django REST Framework in INSTALLED_APPS.'
        )
    if mode == "auto":
        return "drf" if drf else "django"
    return mode


def api_view():
    """The view the URL uses (decided once, when the URLs load)."""
    if api_mode() == "drf":
        from .api_drf import ThemeAPIView  # only imported when DRF is installed

        return ThemeAPIView.as_view()
    return theme_api


def catalog_view():
    """The view for /theme/themes.json (DRF or plain, like api_view)."""
    if api_mode() == "drf":
        from .api_drf import ThemeCatalogAPIView

        return ThemeCatalogAPIView.as_view()
    return theme_catalog_api


def assets_view():
    """The view for /theme/themes/<slug>.json (DRF or plain, like api_view)."""
    if api_mode() == "drf":
        from .api_drf import ThemeAssetsAPIView

        return ThemeAssetsAPIView.as_view()
    return theme_assets_api
