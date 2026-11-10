"""Template tags for putting the active theme on a page.

Load them with `{% load capy_theme %}`. Put `{% theme_html_attrs %}` inside the
page's <html> tag and `{% theme_head %}` inside <head>. The README shows a full example.
"""

from django import template
from django.urls import reverse
from django.utils.html import format_html

from ..active import get_active_theme

register = template.Library()


@register.simple_tag(takes_context=True)
def theme_head(context):
    """Output the <link> to the active theme's stylesheet, or nothing if no theme is active."""
    theme = get_active_theme(context.get("request"))
    if theme is None or theme.live_revision is None:
        return ""
    url = reverse("capy_theme:theme_css", args=[theme.live_revision.css_version])
    return format_html('<link rel="stylesheet" href="{}">', url)


@register.simple_tag(takes_context=True)
def theme_html_attrs(context):
    """Output attributes for the page's <html> tag.

    Nothing yet: the stylesheet sets the colours and follows the visitor's
    light/dark device setting. The light/dark toggle (6.1) will use this to
    force a mode. Put it in templates now so they don't need changing later.
    """
    return ""
