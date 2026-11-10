"""Site icons: every favicon and app icon, made from the theme's one square icon.

The icon image is chosen like a logo (`settings["images"]["icon"]`, light and
optionally dark). `settings["icon"]` has the background colour and padding.

The files are made when the theme is published, in a folder named after the
icon image and those settings, so each published revision keeps its own icons
and publishing the same icon again reuses them.
"""

import base64
import hashlib
import io
import json
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe
from PIL import Image, ImageOps

_DATA = json.loads(Path(__file__).with_name("icons.json").read_text(encoding="utf-8"))

# From icons.json. name: (size in px, what it is)
FILES = {name: (f["size"], f["label"]) for name, f in _DATA["files"].items()}
# name: (label, help)
SETTINGS = {name: (s["label"], s["help"]) for name, s in _DATA["settings"].items()}
# Home-screen icons can't be transparent; this is used if no background is set.
OPAQUE_FALLBACK = "#ffffff"
VERSION = "1"  # change when the way icons are made changes, so they're remade


def icon_folder(snapshot):
    """Where this revision's icon files are, or None if the theme has no icon."""
    icon = snapshot.get("images", {}).get("icon", {})
    if "light" not in icon and "dark" not in icon:
        return None
    key = json.dumps(
        [VERSION, {m: i["file"] for m, i in icon.items()}, snapshot["settings"].get("icon", {})],
        sort_keys=True,
    )
    return f"capy_theme/icons/{hashlib.sha256(key.encode()).hexdigest()[:16]}"


def make_icons(snapshot):
    """Create the icon files for a snapshot, unless they already exist."""
    folder = icon_folder(snapshot)
    if folder is None or default_storage.exists(f"{folder}/{list(FILES)[-1]}"):
        return
    icon = snapshot["images"]["icon"]
    light = _open(icon.get("light") or icon["dark"])
    dark = _open(icon["dark"]) if "dark" in icon else None
    settings = snapshot["settings"].get("icon", {})
    background = settings.get("background") or None
    padding = settings.get("padding", 0) / 100
    files = {
        "favicon.ico": _ico(_square(light, 48, padding, background)),
        "favicon.svg": _svg(light, dark, padding, background),
        "apple-touch-icon.png": _png(_square(light, 180, padding, background or OPAQUE_FALLBACK)),
        "icon-192.png": _png(_square(light, 192, padding, background)),
        "icon-512.png": _png(_square(light, 512, padding, background)),
        # The maskable icon's visible part is the middle 80%, so it gets 10%
        # extra space on each side and a solid background.
        "icon-maskable-512.png": _png(
            _square(light, 512, padding * 0.8 + 0.1, background or OPAQUE_FALLBACK)
        ),
        "icon-monochrome-512.png": _png(_monochrome(_square(light, 512, padding, None))),
    }
    # Written last-first, so the existence check above only passes once all are there.
    for name in reversed(FILES):
        default_storage.save(f"{folder}/{name}", ContentFile(files[name]))


def head_links(snapshot):
    """The <link> tags for {% theme_head %}: tab icons and the Apple icon."""
    folder = icon_folder(snapshot)
    if folder is None:
        return ""
    url = default_storage.url
    links = [
        ("icon", url(f"{folder}/favicon.ico"), ' sizes="32x32"'),
        ("icon", url(f"{folder}/favicon.svg"), ' type="image/svg+xml"'),
        ("icon", url(f"{folder}/icon-192.png"), ' type="image/png" sizes="192x192"'),
        ("apple-touch-icon", url(f"{folder}/apple-touch-icon.png"), ""),
    ]
    return format_html_join(
        "",
        '<link rel="{}" href="{}"{}>\n',
        ((r, h, mark_safe(e)) for r, h, e in links),  # noqa: S308 (fixed text above)
    )


def icon_urls(snapshot):
    """{file name: URL} for this revision's icons (other modules get them via artifacts)."""
    folder = icon_folder(snapshot)
    if folder is None:
        return {}
    return {name: default_storage.url(f"{folder}/{name}") for name in FILES}


def _open(image):
    with default_storage.open(image["file"], "rb") as file:
        opened = Image.open(file)
        opened.load()
    return opened.convert("RGBA")


def _square(image, size, padding, background):
    """The image centred on a square canvas, with padding (a fraction of the size)."""
    canvas = Image.new("RGBA", (size, size), background or (0, 0, 0, 0))
    inner = max(1, round(size * (1 - 2 * padding)))
    fitted = ImageOps.contain(image, (inner, inner), Image.Resampling.LANCZOS)
    canvas.alpha_composite(fitted, ((size - fitted.width) // 2, (size - fitted.height) // 2))
    return canvas


def _monochrome(image):
    """White, with the icon's shape as transparency: only the shape counts.

    Transparent icons use their own transparency. Fully opaque ones use darkness,
    so a dark mark on a light square still gives the mark.
    """
    alpha = image.getchannel("A")
    if alpha.getextrema()[0] == 255:
        alpha = ImageOps.invert(image.convert("L"))
    white = Image.new("RGBA", image.size, (255, 255, 255, 0))
    white.putalpha(alpha)
    return white


def _png(image):
    output = io.BytesIO()
    image.save(output, "PNG", optimize=True)
    return output.getvalue()


def _ico(image):
    output = io.BytesIO()
    image.save(output, "ICO", sizes=[(16, 16), (32, 32), (48, 48)])
    return output.getvalue()


def _svg(light, dark, padding, background):
    """An SVG favicon with the PNG inside; with a dark icon, it switches by itself."""

    def data(image):
        png = _png(_square(image, 64, padding, background))
        return "data:image/png;base64," + base64.b64encode(png).decode()

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">',
        f'<image class="light" href="{data(light)}" width="64" height="64"/>',
    ]
    if dark is not None:
        parts += [
            "<style>.dark{display:none}@media (prefers-color-scheme: dark)"
            "{.light{display:none}.dark{display:inline}}</style>",
            f'<image class="dark" href="{data(dark)}" width="64" height="64"/>',
        ]
    parts.append("</svg>")
    return "".join(parts).encode()
