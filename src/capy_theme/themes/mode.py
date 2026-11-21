"""Light, dark or auto: which color mode a page uses.

The theme sets a default mode ("auto" follows the visitor's device) and whether
visitors can switch. A visitor's choice is kept in a cookie. Forced modes use the
stylesheet's [data-theme="capy-light"] / [data-theme="capy-dark"] rules on <html>.
"""

import json

from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.http import urlencode

from ..colors.color_math import to_hex
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


def mode_state(request, revision):
    """The light/dark/auto state as plain data, for a consumer to render its own control.

    Returns {"can_switch", "current", "options", "next"}. Each option is
    {"value", "label", "url", "current"}, where "url" sets that mode and returns to the
    current page (so a plain link works without JavaScript). "next" is the mode a single
    cycling button advances to. The head script enhances any element carrying
    ``data-capy-mode`` (set that mode) or ``data-capy-mode-cycle`` (advance to the next
    mode) to switch without a reload. See docs/artifacts.md.

    When the theme doesn't allow switching, ``can_switch`` is False, ``options`` is empty
    and ``next`` is None (switching is a no-op server- and client-side), so a consumer
    that loops ``options`` renders no control. Render the mode control only when
    ``can_switch`` is true.
    """
    _default, can_switch = mode_settings(revision)
    current = current_mode(request, revision)
    if not can_switch:
        return {"can_switch": False, "current": current, "options": [], "next": None}
    back = request.get_full_path() if request is not None else "/"

    def set_url(value):
        return reverse("capy_theme:set_mode", args=[value]) + "?" + urlencode({"next": back})

    options = [
        {
            "value": mode,
            "label": MODE_LABELS[mode],
            "url": set_url(mode),
            "current": mode == current,
        }
        for mode in MODES
    ]
    order = list(MODES)
    after = order[(order.index(current) + 1) % len(order)]
    return {
        "can_switch": can_switch,
        "current": current,
        "options": options,
        "next": {"value": after, "label": MODE_LABELS[after], "url": set_url(after)},
    }


def head_script(revision):
    """Return the tiny script that applies the mode before the page draws.

    It repeats the server's choice from the cookie (so cached pages are right too) and
    keeps ``<html data-capy-color-mode>`` in sync. It switches without reloading when a
    visitor clicks any element carrying ``data-capy-mode`` (set that mode) or
    ``data-capy-mode-cycle`` (advance light -> dark -> auto), and dispatches a
    ``capy:modechange`` event (``detail: {mode}``) on ``document`` so a consumer can
    announce the change to assistive technology. See docs/artifacts.md.
    """
    default, can_switch = mode_settings(revision)
    return (
        "(function(){var d=document.documentElement,n="
        + json.dumps(COOKIE_NAME)
        + ",f="
        + json.dumps(default)
        + ",s="
        + json.dumps(bool(can_switch))
        + ",O="
        + json.dumps(list(MODES))
        + ";"
        "function cur(){var m=(document.cookie.match(new RegExp('(?:^|; )'+n+"
        "'=(light|dark|auto)(?:;|$)'))||[])[1];return s&&m?m:f}"
        "function apply(m){if(m==='auto')d.removeAttribute('data-theme');"
        "else d.setAttribute('data-theme','capy-'+m);"
        "d.setAttribute('data-capy-color-mode',m);"
        "document.querySelectorAll('[data-capy-mode]').forEach(function(e){"
        "var on=e.getAttribute('data-capy-mode')===m;"
        "if(on)e.setAttribute('aria-current','true');else e.removeAttribute('aria-current');"
        "e.classList.toggle('btn-active',on)})}"
        "function set(m){document.cookie=n+'='+m+';path=/;max-age="
        + str(COOKIE_MAX_AGE)
        + ";samesite=lax'+(location.protocol==='https:'?';secure':'');apply(m);"
        "document.dispatchEvent(new CustomEvent('capy:modechange',{detail:{mode:m}}))}"
        "apply(cur());"
        "document.addEventListener('click',function(e){if(!s)return;"
        "var t=e.target.closest&&e.target.closest('[data-capy-mode],[data-capy-mode-cycle]');"
        "if(!t)return;e.preventDefault();"
        "if(t.hasAttribute('data-capy-mode-cycle'))set(O[(O.indexOf(cur())+1)%O.length]);"
        "else set(t.getAttribute('data-capy-mode'))})})();"
    )


def theme_color_meta(revision, mode):
    """The <meta name="theme-color"> tags: the browser's address-bar color.

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
