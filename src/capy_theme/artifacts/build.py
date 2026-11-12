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

from django.core.files.storage import default_storage

from ..colors.color_math import to_hex
from ..colors.names import COLOR_NAMES, SCHEMES
from ..colors.values import effective_values
from ..css.backgrounds import VARIABLES as BACKGROUND_SLOTS
from ..css.shape import EFFECTS, SIZES
from ..css.stylesheet import stylesheet_url
from ..fonts.library import ROLES, stack
from ..images.icons import icon_urls
from ..images.logos import HEADER_SLOTS, LOGO_SLOTS, resolve
from ..images.sharing import sharing_image
from ..themes.active import get_active_theme
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
                        "url": url(f["url"]),
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
            "url": url(default_storage.url(share["file"])),
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


def _url_maker(request):
    if request is None:
        return lambda path: path
    return request.build_absolute_uri


def _file_url(image, url):
    return url(default_storage.url(image["file"])) if image else None


def _image(image, slot, url, alt):
    if image is None:
        return None
    variants = image.get("variants", []) if slot in HEADER_SLOTS else []
    return {
        "url": url(default_storage.url(image["file"])),
        "width": image["width"],
        "height": image["height"],
        "alt": image.get("alt") or alt,
        "content_type": image.get("content_type", ""),
        "variants": [
            {"url": url(default_storage.url(v["file"])), "width": v["width"], "format": v["format"]}
            for v in variants
            if not v.get("purpose")
        ],
    }
