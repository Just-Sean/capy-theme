"""The draft's logos and icon, for previewing them on the page before publishing (#271).

The editor (controls/page-images.js) swaps the page's logos, and the browser-tab icon,
for these. Only in the editing user's browser.
"""

from ..images.logos import LOGO_SLOTS, resolve
from ..storage import theme_storage


def page_images(snapshot):
    """{"logos": {slot: image or None}, "site_name", "icon": url}, where image is
    {src, alt, width, height} or None. Follows the same fallbacks as the published
    logos."""
    settings = snapshot.get("settings", {})
    alt = settings.get("logo_alt") or settings.get("site_name", "")
    logos = {slot: _image(resolve(snapshot, slot), alt) for slot in LOGO_SLOTS}
    icon = resolve(snapshot, "icon")
    return {
        "logos": logos,
        "site_name": settings.get("site_name", ""),
        "icon": theme_storage().url(icon["file"]) if icon else "",
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
