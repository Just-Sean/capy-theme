"""Template tags for putting the active theme on a page.

Load them with `{% load capy_theme %}`. Put `{% theme_html_attrs %}` inside the
page's <html> tag and `{% theme_head %}` inside <head>. The README shows a full example.
"""

from django import template
from django.utils.html import format_html, format_html_join

from ..active import get_active_theme
from ..branding import branding
from ..stylesheet import stylesheet_url

register = template.Library()


@register.simple_tag(takes_context=True)
def theme_head(context):
    """Output the <link> to the active theme's stylesheet, or nothing if no theme is active."""
    theme = get_active_theme(context.get("request"))
    if theme is None or theme.live_revision is None:
        return ""
    url = stylesheet_url(theme.live_revision)
    return format_html('<link rel="stylesheet" href="{}">', url)


@register.simple_tag(takes_context=True)
def theme_html_attrs(context):
    """Output attributes for the page's <html> tag.

    Nothing yet: the stylesheet sets the colours and follows the visitor's
    light/dark device setting. The light/dark toggle (6.1) will use this to
    force a mode. Put it in templates now so they don't need changing later.
    """
    return ""


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
