"""Light, dark or auto: which colour mode a page uses.

The theme sets a default mode ("auto" follows the visitor's device) and whether
visitors can switch. A visitor's choice is kept in a cookie. Forced modes use the
stylesheet's [data-theme="capy-light"] / [data-theme="capy-dark"] rules on <html>.
"""

import json

from django.utils.html import format_html, format_html_join

from ..colors.maths import to_hex
from ..colors.names import SCHEMES
from ..colors.values import effective_values

MODES = ("light", "dark", "auto")
MODE_LABELS = {"light": "Light", "dark": "Dark", "auto": "Auto"}
COOKIE_NAME = "capy_theme_mode"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # a year, so the choice survives closing the browser


def mode_settings(revision):
    """Return (default_mode, visitors_can_switch) from a published revision."""
    settings = revision.snapshot.get("settings", {})
    return settings.get("default_mode", "auto"), settings.get("visitors_can_switch", True)


def current_mode(request, revision):
    """Return the mode to show: the visitor's choice if allowed, else the theme's default."""
    default, can_switch = mode_settings(revision)
    choice = request.COOKIES.get(COOKIE_NAME) if request is not None else None
    if can_switch and choice in MODES:
        return choice
    return default


def html_theme_value(mode):
    """Return the data-theme value that forces a mode, or "" for auto."""
    return f"capy-{mode}" if mode in ("light", "dark") else ""


def head_script(revision):
    """Return the tiny script that applies the mode before the page draws.

    It repeats the server's choice from the cookie (so cached pages are right
    too), and makes {% theme_mode_toggle %} switch without reloading.
    """
    default, can_switch = mode_settings(revision)
    return (
        "(function(){var d=document.documentElement,n="
        + json.dumps(COOKIE_NAME)
        + ",f="
        + json.dumps(default)
        + ",s="
        + json.dumps(bool(can_switch))
        + ";"
        "function cur(){var m=(document.cookie.match(new RegExp('(?:^|; )'+n+"
        "'=(light|dark|auto)(?:;|$)'))||[])[1];return s&&m?m:f}"
        "function apply(m){if(m==='auto')d.removeAttribute('data-theme');"
        "else d.setAttribute('data-theme','capy-'+m);"
        "document.querySelectorAll('[data-capy-mode]').forEach(function(e){"
        "var on=e.getAttribute('data-capy-mode')===m;"
        "if(on)e.setAttribute('aria-current','true');else e.removeAttribute('aria-current');"
        "e.classList.toggle('btn-active',on)})}"
        "apply(cur());"
        "document.addEventListener('click',function(e){"
        "var a=e.target.closest&&e.target.closest('[data-capy-mode]');if(!a||!s)return;"
        "e.preventDefault();var m=a.getAttribute('data-capy-mode');"
        "document.cookie=n+'='+m+';path=/;max-age=" + str(COOKIE_MAX_AGE) + ";samesite=lax';"
        "apply(m)})})();"
    )


def theme_color_meta(revision, mode):
    """The <meta name="theme-color"> tags: the browser's address-bar colour.

    Matches the page background. With a forced mode, one tag for that mode;
    otherwise one each for light and dark, chosen by the device setting.
    """
    colors = {
        scheme: to_hex(effective_values(revision.snapshot, scheme)["--color-base-100"], alpha=False)
        for scheme in SCHEMES
    }
    if mode in SCHEMES:
        return format_html('<meta name="theme-color" content="{}">\n', colors[mode])
    return format_html_join(
        "",
        '<meta name="theme-color" media="(prefers-color-scheme: {})" content="{}">\n',
        ((scheme, colors[scheme]) for scheme in SCHEMES),
    )
