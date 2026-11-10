from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ImproperlyConfigured
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme

from .active import get_active_theme
from .branding import branding
from .mode import COOKIE_MAX_AGE, COOKIE_NAME, MODES, mode_settings
from .models import ThemeRevision
from .stylesheet import render_css

ONE_YEAR = 60 * 60 * 24 * 365


def theme_css(request, version):
    """Serve a revision's stylesheet. Every URL names one revision, so it never changes."""
    revision = get_object_or_404(ThemeRevision.objects.select_related("theme"), css_version=version)
    response = HttpResponse(render_css(revision), content_type="text/css; charset=utf-8")
    response["Cache-Control"] = f"public, max-age={ONE_YEAR}, immutable"
    return response


# The showcase page. Each section is its own template in
# templates/capy_theme/showcase/sections/, shown once per mode. Later phases add
# their sections by adding a template and a name here.
SHOWCASE_SECTIONS = [
    "branding",
    "typography",
    "buttons",
    "badges",
    "alerts",
    "cards",
    "tabs",
    "table",
    "forms",
    "progress",
    "modal",
]
SHOWCASE_ACCESS = ("staff", "public", "off")


def showcase(request):
    """Show the active theme's choices on every kind of component, in light and dark."""
    access = getattr(settings, "CAPY_THEME_SHOWCASE", "staff")
    if access not in SHOWCASE_ACCESS:
        raise ImproperlyConfigured(
            f"CAPY_THEME_SHOWCASE must be one of {', '.join(SHOWCASE_ACCESS)}, not {access!r}."
        )
    if access == "off":
        raise Http404("The theme showcase is turned off.")
    if access == "staff" and not (request.user.is_active and request.user.is_staff):
        return redirect_to_login(request.get_full_path(), reverse("admin:login"))

    theme = get_active_theme(request)
    revision = theme.live_revision if theme else None
    context = {
        "base_template": getattr(
            settings, "CAPY_THEME_BASE_TEMPLATE", "capy_theme/showcase/standalone.html"
        ),
        "active_theme": theme,
        "revision": revision,
        "brand": branding(revision) if revision else {},
        "modes": ["light", "dark"],
        "sections": [f"capy_theme/showcase/sections/{name}.html" for name in SHOWCASE_SECTIONS],
    }
    return render(request, "capy_theme/showcase/page.html", context)


def set_mode(request, mode):
    """Remember a visitor's light/dark/auto choice in a cookie, then go back.

    Used by {% theme_mode_toggle %} when JavaScript is off (with JavaScript the
    script sets the cookie itself). Ignored if the theme doesn't allow switching.
    """
    if mode not in MODES:
        raise Http404("Unknown mode.")
    target = request.GET.get("next", "/")
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = "/"
    response = HttpResponseRedirect(target)
    theme = get_active_theme(request)
    if theme is not None and theme.live_revision is not None:
        if mode_settings(theme.live_revision)[1]:
            response.set_cookie(
                COOKIE_NAME, mode, max_age=COOKIE_MAX_AGE, samesite="Lax", httponly=False
            )
    return response
