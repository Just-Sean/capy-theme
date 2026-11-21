"""Everything the active theme produces, as plain data for other modules.

capy-theme owns the theme but doesn't apply it outside the page's own look. An
email module, an app shell, a PWA or social-tags module reads what it needs
from here (or from `{% theme_artifacts as theme_artifacts %}` in templates):

    from capy_theme.artifacts import get_artifacts

    artifacts = get_artifacts(request)
    if artifacts:
        logo = artifacts["logos"]["logo_email"]["light"]["url"]
        primary = artifacts["colors_hex"]["light"]["primary"]
        icon = artifacts["icons"].get("icon-512.png")

Everything comes from the published revision, never the draft. With a request,
every URL is absolute (e.g. for emails and manifests).
"""

from django.urls import reverse

from ..colors.color_math import to_hex
from ..colors.names import COLOR_NAMES, SCHEMES
from ..colors.values import effective_values
from ..css.backgrounds import VARIABLES as BACKGROUND_SLOTS
from ..css.shape import EFFECTS, SIZES
from ..css.stylesheet import stylesheet_url
from ..fonts.library import ROLES, font_file_url, stack
from ..images.icons import icon_urls
from ..images.logos import HEADER_SLOTS, LOGO_SLOTS, resolve
from ..images.sharing import sharing_image
from ..storage import theme_storage
from ..themes.active import default_theme, get_active_theme, offered_themes
from ..themes.branding import branding
from ..themes.mode import mode_settings


def get_artifacts(request=None):
    """The active theme's published artifacts, or None if no theme is published.

    Returns a dict:

    - "theme": {"name", "slug", "revision"}
    - "branding": {"site_name", "tagline", "logo_alt"}
    - "colors": {"light"|"dark": {"primary": "oklch(…)", "base-100": …}} (all 20)
    - "colors_hex": the same as #rrggbb (for emails and other non-CSS uses)
    - "fonts": {role: {"family", "stack", "source", "stylesheet", "files"}} for the
      roles the theme sets; "files" are [{"url", "weight", "style", "unicode_range"}]
      ("stylesheet" is the external stylesheet URL for external fonts, else "")
    - "shape": {"light"|"dark": {setting: CSS value}}: radii, sizes, border, depth
      and noise (e.g. "radius_box": "0.5rem")
    - "type": the type scale settings the theme sets (e.g. {"base_size": 18})
    - "logos": {slot: {"light"|"dark": image or None}} for the six logo slots,
      after fallbacks (an empty slot gives the main logo; dark gives light)
    - "icons": {file name: URL} (favicon.ico, favicon.svg, apple-touch-icon.png,
      icon-192.png, icon-512.png, icon-maskable-512.png, icon-monochrome-512.png);
      {} without an icon
    - "sharing_image": {"url", "width", "height", "alt"} (1200 × 630) or None
    - "backgrounds": {"login"|"pattern": {"light"|"dark": URL or None}}
    - "mode": {"default", "visitors_can_switch"}
    - "stylesheet_url"

    An image is {"url", "width", "height", "alt", "content_type", "variants":
    [{"url", "width", "format"}]}; variants are the smaller copies (header logos
    only).
    """
    theme = get_active_theme(request)
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
    default_mode, can_switch = mode_settings(revision)
    values = {scheme: effective_values(snapshot, scheme) for scheme in SCHEMES}
    share = sharing_image(snapshot)
    return {
        "theme": {"name": theme.name, "slug": theme.slug, "revision": revision.number},
        "branding": {
            "site_name": brand["site_name"],
            "tagline": brand["tagline"],
            "logo_alt": brand["logo_alt"],
        },
        "colors": {
            scheme: {name: values[scheme][f"--color-{name}"] for name in COLOR_NAMES}
            for scheme in SCHEMES
        },
        "colors_hex": {
            scheme: {
                name: to_hex(values[scheme][f"--color-{name}"], alpha=False) for name in COLOR_NAMES
            }
            for scheme in SCHEMES
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
            scheme: {
                name: values[scheme][spec[0]]
                for name, spec in (SIZES | EFFECTS).items()
                if spec[0] in values[scheme]
            }
            for scheme in SCHEMES
        },
        "type": dict(snapshot.get("settings", {}).get("type", {})),
        "logos": {
            slot: {
                scheme: _image(resolve(snapshot, slot, scheme), slot, url, brand["logo_alt"])
                for scheme in SCHEMES
            }
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
            slot.removeprefix("background_"): {
                scheme: _file_url(resolve(snapshot, slot, scheme), url) for scheme in SCHEMES
            }
            for slot in BACKGROUND_SLOTS
        },
        "mode": {"default": default_mode, "visitors_can_switch": can_switch},
        "stylesheet_url": url(stylesheet_url(revision)),
    }


def theme_catalog(request=None):
    """The available themes as plain data, for a consumer to render its own picker.

    Each entry: ``slug``, ``name``, ``default`` (the admin's default theme), ``light``
    and ``dark`` (each ``{"base", "swatch", "background"}`` — the daisyUI base and the
    primary/background colors as #rrggbb), and ``assets_url`` / ``stylesheet_url``. Lists
    the themes offered to visitors, plus the default; ``[]`` if none is published. With a
    request, every URL is absolute.
    """
    url = _url_maker(request)
    default = default_theme()
    default_slug = default.slug if default else None
    themes = list(offered_themes())
    if default is not None and default.slug not in {theme.slug for theme in themes}:
        themes.append(default)
    themes.sort(key=lambda theme: theme.name)
    return [_catalog_entry(theme, url, default_slug) for theme in themes]


def _catalog_entry(theme, url, default_slug):
    snapshot = theme.live_revision.snapshot
    values = {scheme: effective_values(snapshot, scheme) for scheme in SCHEMES}

    def side(scheme, base):
        colors = values[scheme]
        return {
            "base": base,
            "swatch": to_hex(colors["--color-primary"], alpha=False),
            "background": to_hex(colors["--color-base-100"], alpha=False),
        }

    return {
        "slug": theme.slug,
        "name": theme.name,
        "default": theme.slug == default_slug,
        "light": side("light", snapshot["light_base"]),
        "dark": side("dark", snapshot["dark_base"]),
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
