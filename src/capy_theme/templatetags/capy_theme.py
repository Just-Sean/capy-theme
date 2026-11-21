"""Template tags for reading the active theme's data from a Django template.

Load them with ``{% load capy_theme %}``. capy-theme exposes data; it does not render UI
or apply a theme to a page — a consumer links the stylesheet and builds its own chrome
from the data (see docs/artifacts.md and the catalog / per-theme endpoints).
"""

from django import template

from ..artifacts import get_artifacts

register = template.Library()


@register.simple_tag(takes_context=True)
def theme_artifacts(context):
    """The active theme's artifacts (see capy_theme.artifacts), for templates.

    ``{% theme_artifacts as artifacts %}`` then e.g.
    ``{{ artifacts.logos.logo_email.light.url }}`` or ``{{ artifacts.icons.icon-192.png }}``
    (use ``artifacts.icons|capy_get:"icon-192.png"`` for names with dots).
    None if no theme is published. URLs are absolute.
    """
    return get_artifacts(context.get("request"))


@register.filter
def capy_get(mapping, key):
    """Look up a dict value by a variable key: ``{{ swatches|capy_get:mode }}``."""
    return mapping.get(key) if hasattr(mapping, "get") else None
