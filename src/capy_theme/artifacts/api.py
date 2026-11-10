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
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponseNotModified, JsonResponse
from django.views.decorators.http import require_GET

from .build import get_artifacts

API_MODES = ("auto", "drf", "django")
CACHE_CONTROL = "public, max-age=60"  # short: the address stays the same after publishing


def payload(request):
    """(data, ETag) for the API, or (None, None) if no theme is published."""
    data = get_artifacts(request)
    if data is None:
        return None, None
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
    return data, '"' + hashlib.sha256(canonical).hexdigest()[:32] + '"'


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
    response["Cache-Control"] = CACHE_CONTROL
    return response


def api_mode():
    """ "drf" or "django": which view serves the API in this project."""
    mode = getattr(settings, "CAPY_THEME_API", "auto")
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
