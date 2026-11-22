"""Everything a published theme produces, as plain data for other modules.

capy-theme owns the theme but doesn't apply it outside the page's own look. An
email module, an app shell, a PWA or social-tags module reads what it needs
from here (or from `{% theme_artifacts as theme_artifacts %}` in templates):

    from capy_theme.artifacts import get_artifacts

    artifacts = get_artifacts(request)
    if artifacts:
        logo = artifacts["logos"]["logo_email"]["url"]
        primary = artifacts["colors"]["primary"]
        icon = artifacts["icons"].get("icon-512.png")

A theme is a single scheme (light or dark), so its colors, shape, logos and
backgrounds are one set, not split by mode. Everything comes from the published
revision, never the draft. With a request, every URL is absolute (e.g. for
emails and manifests).
"""

from django.urls import reverse

from ..colors.color_math import to_hex
from ..colors.names import COLOR_NAMES
from ..colors.values import effective_values
from ..css.backgrounds import VARIABLES as BACKGROUND_SLOTS
from ..css.shape import EFFECTS, SIZES
from ..css.stylesheet import stylesheet_url
from ..fonts.library import ROLES, font_file_url, stack
from ..images.icons import icon_urls
from ..images.logos import HEADER_SLOTS, LOGO_SLOTS, resolve
from ..images.sharing import sharing_image
from ..storage import theme_storage
from ..themes.active import default_themes, offered_themes, primary_theme
from ..themes.branding import branding


def get_artifacts(request=None):
    """The domain's primary theme's published artifacts, or None if none is published.

    The primary theme is the domain's default light theme (or its default dark
    theme if no light default is set) — the one a single-theme consumer such as
    an email or a PWA manifest reads. Returns a dict:

    - "theme": {"name", "slug", "scheme", "revision"}
    - "branding": {"site_name", "tagline", "logo_alt"}
    - "colors": {"primary": "oklch(…)", "base-100": …} (all 20)
    - "colors_hex": the same as #rrggbb (for emails and other non-CSS uses)
    - "fonts": {role: {"family", "stack", "source", "stylesheet", "files"}} for the
      roles the theme sets; "files" are [{"url", "weight", "style", "unicode_range"}]
      ("stylesheet" is the external stylesheet URL for external fonts, else "")
    - "shape": {setting: CSS value}: radii, sizes, border, depth and noise
      (e.g. "radius_box": "0.5rem")
    - "type": the type scale settings the theme sets (e.g. {"base_size": 18})
    - "logos": {slot: image or None} for the six logo slots, after fallbacks
      (an empty slot gives the main logo)
    - "icons": {file name: URL} (favicon.ico, favicon.svg, apple-touch-icon.png,
      icon-192.png, icon-512.png, icon-maskable-512.png, icon-monochrome-512.png);
      {} without an icon
    - "sharing_image": {"url", "width", "height", "alt"} (1200 × 630) or None
    - "backgrounds": {"login"|"pattern": URL or None}
    - "stylesheet_url"

    An image is {"url", "width", "height", "alt", "content_type", "variants":
    [{"url", "width", "format"}]}; variants are the smaller copies (header logos
    only).
    """
    theme = primary_theme(request)
    if theme is None or theme.live_revision is None:
        return None
    return build_artifacts(theme, request)


def build_artifacts(theme, request=None):
    """A published theme's artifacts as a dict, in the same shape as get_artifacts().

    ``theme`` must have a live revision. With a request, every URL is absolute.
    """
    revision = theme.live_revision
    snapshot = revision.snapshot
    url = _url_maker(request)
    brand = branding(revision)
    values = effective_values(snapshot)
    share = sharing_image(snapshot)
    return {
        "theme": {
            "name": theme.name,
            "slug": theme.slug,
            "scheme": snapshot["scheme"],
            "revision": revision.number,
        },
        "branding": {
            "site_name": brand["site_name"],
            "tagline": brand["tagline"],
            "logo_alt": brand["logo_alt"],
        },
        "colors": {name: values[f"--color-{name}"] for name in COLOR_NAMES},
        "colors_hex": {
            name: to_hex(values[f"--color-{name}"], alpha=False) for name in COLOR_NAMES
        },
        "fonts": {
            role: {
                "family": font["family"],
                "stack": stack(role, font),
                "source": font["source"],
                "stylesheet": font.get("stylesheet") or "",
                "files": [
                    {
                        "url": url(font_file_url(f)),
                        "weight": f["weight"],
                        "style": f["style"],
                        "unicode_range": f["unicode_range"],
                    }
                    for f in font.get("files", [])
                ],
            }
            for role, font in snapshot.get("fonts", {}).items()
            if role in ROLES
        },
        "shape": {
            name: values[spec[0]] for name, spec in (SIZES | EFFECTS).items() if spec[0] in values
        },
        "type": dict(snapshot.get("settings", {}).get("type", {})),
        "logos": {
            slot: _image(resolve(snapshot, slot), slot, url, brand["logo_alt"])
            for slot in LOGO_SLOTS
        },
        "icons": {name: url(path) for name, path in icon_urls(snapshot).items()},
        "sharing_image": {
            "url": url(theme_storage().url(share["file"])),
            "width": share["width"],
            "height": share["height"],
            "alt": share["alt"],
        }
        if share
        else None,
        "backgrounds": {
            slot.removeprefix("background_"): _file_url(resolve(snapshot, slot), url)
            for slot in BACKGROUND_SLOTS
        },
        "stylesheet_url": url(stylesheet_url(revision)),
    }


def theme_catalog(request=None):
    """The available themes as plain data, for a consumer to render its own picker.

    Each entry: ``slug``, ``name``, ``scheme`` (``"light"`` or ``"dark"``),
    ``default`` (whether it's the domain's default theme **for its scheme**),
    ``swatch`` and ``background`` (the primary/background colors as #rrggbb), and
    ``assets_url`` / ``stylesheet_url``. Lists the themes offered to visitors, plus
    the **domain's** default light and dark themes. ``[]`` if none is published.
    With a request, every URL is absolute.
    """
    url = _url_maker(request)
    defaults = default_themes(request)
    default_slug = {scheme: (theme.slug if theme else None) for scheme, theme in defaults.items()}
    themes = list(offered_themes())
    offered_slugs = {theme.slug for theme in themes}
    for theme in defaults.values():
        if theme is not None and theme.slug not in offered_slugs:
            themes.append(theme)
            offered_slugs.add(theme.slug)
    # Only published themes have a snapshot to read; skip any without one so a theme
    # that somehow lost its live revision can't 500 the whole catalog.
    themes = [theme for theme in themes if theme.live_revision_id is not None]
    themes.sort(key=lambda theme: theme.name)
    return [_catalog_entry(theme, url, default_slug) for theme in themes]


def _catalog_entry(theme, url, default_slug):
    snapshot = theme.live_revision.snapshot
    scheme = snapshot["scheme"]
    values = effective_values(snapshot)
    return {
        "slug": theme.slug,
        "name": theme.name,
        "scheme": scheme,
        "default": theme.slug == default_slug.get(scheme),
        "swatch": to_hex(values["--color-primary"], alpha=False),
        "background": to_hex(values["--color-base-100"], alpha=False),
        "assets_url": url(reverse("capy_theme:theme_assets", args=[theme.slug])),
        "stylesheet_url": url(stylesheet_url(theme.live_revision)),
    }


def _url_maker(request):
    if request is None:
        return lambda path: path
    return request.build_absolute_uri


def _file_url(image, url):
    return url(theme_storage().url(image["file"])) if image else None


def _image(image, slot, url, alt):
    if image is None:
        return None
    variants = image.get("variants", []) if slot in HEADER_SLOTS else []
    return {
        "url": url(theme_storage().url(image["file"])),
        "width": image["width"],
        "height": image["height"],
        "alt": image.get("alt") or alt,
        "content_type": image.get("content_type", ""),
        "variants": [
            {"url": url(theme_storage().url(v["file"])), "width": v["width"], "format": v["format"]}
            for v in variants
            if not v.get("purpose")
        ],
    }
