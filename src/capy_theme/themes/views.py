"""Visitors' choices: light/dark/auto and the offered themes (stored in cookies)."""

from django.http import Http404, HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme

from .active import (
    CHOICE_COOKIE,
    get_active_theme,
    offered_themes,
    visitor_themes_allowed,
)
from .mode import COOKIE_MAX_AGE, COOKIE_NAME, MODES, mode_settings


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


def choose_theme(request, slug):
    """Remember a visitor's theme choice in a cookie, then go back.

    `slug` is an offered theme's slug, or "default" for the site's own theme.
    Themes that aren't offered to visitors are ignored, so they can't be forced.
    """
    target = request.GET.get("next", "/")
    if not url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        target = "/"
    response = HttpResponseRedirect(target)
    offered = {theme.slug for theme in offered_themes()}
    if slug == "default":
        response.delete_cookie(CHOICE_COOKIE, samesite="Lax")
    elif visitor_themes_allowed() and slug in offered:
        response.set_cookie(
            CHOICE_COOKIE, slug, max_age=COOKIE_MAX_AGE, samesite="Lax", httponly=True
        )
    return response
