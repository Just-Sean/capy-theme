"""The draft's logos and icon, for previewing them on the page before publishing (#271).

The editor (controls/page-images.js) swaps the logos that {% theme_logo %} put on
the page, and the browser-tab icon, for these. Only in the editing user's browser.
"""

from ..images.logos import HEADER_SLOTS, LOGO_SLOTS, resolve
from ..storage import theme_storage


def page_images(snapshot):
    """{"logos": {slot: {"light": image, "dark": image or None}}, "site_name",
    "icon": {"light": url, "dark": url}}, where image is {src, alt, width, height}
    or None. Follows the same fallbacks as the published logos."""
    settings = snapshot.get("settings", {})
    alt = settings.get("logo_alt") or settings.get("site_name", "")
    logos = {}
    for slot in LOGO_SLOTS:
        light = resolve(snapshot, slot, "light")
        dark = resolve(snapshot, slot, "dark") if slot in HEADER_SLOTS else light
        logos[slot] = {
            "light": _image(light, alt),
            "dark": _image(dark, alt) if dark != light else None,
        }
    icon = {mode: resolve(snapshot, "icon", mode) for mode in ("light", "dark")}
    return {
        "logos": logos,
        "site_name": settings.get("site_name", ""),
        "icon": {mode: theme_storage().url(i["file"]) if i else "" for mode, i in icon.items()},
    }


def _image(image, alt):
    if image is None:
        return None
    return {
        "src": theme_storage().url(image["file"]),
        "alt": image.get("alt") or alt,
        "width": image["width"],
        "height": image["height"],
    }
