"""Template tags for reading the active theme's data from a Django template.

Load them with ``{% load capy_theme %}``. capy-theme exposes data; it does not render UI
or apply a theme to a page — a consumer links the stylesheet and builds its own chrome
from the data (see docs/artifacts.md and the catalog / per-theme endpoints).
"""

from django import template

from ..artifacts import build_artifacts, get_artifacts
from ..artifacts import theme_catalog as _theme_catalog
from ..themes.active import catalog_theme

register = template.Library()


@register.simple_tag(takes_context=True)
def theme_artifacts(context):
    """The active theme's artifacts (see capy_theme.artifacts), for templates.

    ``{% theme_artifacts as artifacts %}`` then e.g.
    ``{{ artifacts.logos.logo_email.url }}`` or ``{{ artifacts.icons.icon-192.png }}``
    (use ``artifacts.icons|capy_get:"icon-192.png"`` for names with dots).
    None if no theme is published. URLs are absolute.
    """
    return get_artifacts(context.get("request"))


@register.simple_tag(takes_context=True)
def theme_catalog(context):
    """The available themes as data, for a consumer to render its own picker.

    ``{% theme_catalog as themes %}`` then loop ``themes`` — each is
    ``{slug, name, scheme, default, swatch, background, assets_url, stylesheet_url}``. The
    same data as the ``/theme/themes.json`` endpoint; an empty list when nothing is
    published. See docs/artifacts.md.
    """
    return _theme_catalog(context.get("request"))


@register.simple_tag(takes_context=True)
def theme_assets(context, slug):
    """One theme's assets by slug, for a consumer to apply a chosen theme.

    ``{% theme_assets "ocean" as assets %}`` then e.g. ``{{ assets.stylesheet_url }}``.
    Same shape as ``{% theme_artifacts %}``, for the theme named by ``slug`` (or
    ``"default"``). None for an unknown, unpublished, or not-offered theme.
    See docs/artifacts.md.
    """
    request = context.get("request")
    theme = catalog_theme(slug, request)
    if theme is None or theme.live_revision is None:
        return None
    return build_artifacts(theme, request)


@register.filter
def capy_get(mapping, key):
    """Look up a dict value by a variable key: ``{{ swatches|capy_get:mode }}``."""
    return mapping.get(key) if hasattr(mapping, "get") else None
