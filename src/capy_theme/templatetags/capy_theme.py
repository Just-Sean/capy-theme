"""Template tags for putting the active theme on a page.

Load them with `{% load capy_theme %}`. Put `{% theme_html_attrs %}` inside the
page's <html> tag and `{% theme_head %}` inside <head>. `{% theme_logo %}` and
`{% theme_mode_toggle %}` go wherever they should appear. The README shows a full example.
"""

from django import template
from django.middleware.csp import get_nonce
from django.template.loader import render_to_string
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from ..active import get_active_theme
from ..branding import branding
from ..colors import SCHEMES, effective_values, to_hex
from ..mode import MODE_LABELS, MODES, current_mode, head_script, html_theme_value, mode_settings
from ..stylesheet import stylesheet_url

register = template.Library()


@register.simple_tag(takes_context=True)
def theme_head(context):
    """Output the active theme's stylesheet link, theme-color tags and mode script.

    Also the theme-color meta tags (the browser's address-bar colour). Outputs
    nothing if no theme is active. The script carries the CSP nonce when
    Django's CSP middleware is on.
    """
    request = context.get("request")
    theme = get_active_theme(request)
    if theme is None or theme.live_revision is None:
        return ""
    revision = theme.live_revision
    nonce = get_nonce(request) if request is not None else None
    nonce_attr = format_html(' nonce="{}"', nonce) if nonce else ""
    return format_html(
        '<link rel="stylesheet" href="{}">\n{}<script{}>{}</script>',
        stylesheet_url(revision),
        theme_color_meta(revision, current_mode(request, revision)),
        nonce_attr,
        mark_safe(head_script(revision)),  # noqa: S308 (built from fixed text and JSON values)
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


@register.simple_tag(takes_context=True)
def theme_html_attrs(context):
    """Output attributes for the page's <html> tag.

    When the page should be forced into light or dark (the theme's default, or
    the visitor's choice from {% theme_mode_toggle %}), outputs
    data-theme="capy-light" or "capy-dark". For "auto" it outputs nothing, and
    the stylesheet follows the visitor's device setting.
    """
    request = context.get("request")
    theme = get_active_theme(request)
    if theme is None or theme.live_revision is None:
        return ""
    value = html_theme_value(current_mode(request, theme.live_revision))
    return format_html('data-theme="{}"', value) if value else ""


@register.simple_tag(takes_context=True)
def theme_mode_toggle(context):
    """Output Light / Dark / Auto buttons for visitors, if the theme allows switching."""
    request = context.get("request")
    theme = get_active_theme(request)
    if theme is None or theme.live_revision is None:
        return ""
    if not mode_settings(theme.live_revision)[1]:
        return ""
    return render_to_string(
        "capy_theme/mode_toggle.html",
        {
            "options": [(mode, MODE_LABELS[mode]) for mode in MODES],
            "current": current_mode(request, theme.live_revision),
            "next": request.get_full_path() if request is not None else "/",
        },
    )


@register.simple_tag(takes_context=True)
def theme_logo(context, **attrs):
    """Output the active theme's logo, or its site name if there's no logo.

    Extra attributes are added to the element, e.g. `{% theme_logo class="h-8" %}`.
    Outputs nothing if no theme is active, or it has neither a logo nor a site name.
    """
    theme = get_active_theme(context.get("request"))
    if theme is None or theme.live_revision is None:
        return ""
    brand = branding(theme.live_revision)
    extra = format_html_join("", ' {}="{}"', sorted(attrs.items()))
    if brand["logo_url"]:
        return format_html('<img src="{}" alt="{}"{}>', brand["logo_url"], brand["logo_alt"], extra)
    if brand["site_name"]:
        return format_html("<span{}>{}</span>", extra, brand["site_name"])
    return ""


@register.filter
def capy_get(mapping, key):
    """Look up a dict value by a variable key: {{ swatches|capy_get:mode }}."""
    return mapping.get(key) if hasattr(mapping, "get") else None
