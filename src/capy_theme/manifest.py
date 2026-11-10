"""The web app manifest: what a browser needs to install the site as an app.

Built from the active theme's published revision: `settings["app"]` (names,
description, start URL, display mode, orientation), the site name and tagline
as fallbacks, the background colour, and the icons from icons.py.
"""

from .colors import effective_values, to_hex
from .icons import icon_urls
from .mode import mode_settings

# name: (label, help, choices or None)
APP_SETTINGS = {
    "name": ("App name", "Shown when installing. Blank: the site name.", None),
    "short_name": ("Short name", "Under the icon, at most 12 characters. Blank: the name.", None),
    "description": ("Description", "What the app is for. Blank: the tagline.", None),
    "start_url": ("Start URL", "The page the app opens on, starting with /. Blank: /.", None),
    "display": (
        "Display",
        "How the installed app looks.",
        [
            ("standalone", "Standalone: its own window, no browser bar (default)"),
            ("minimal-ui", "Minimal: its own window with back and reload buttons"),
            ("fullscreen", "Full screen"),
            ("browser", "Browser: opens in a normal browser tab"),
        ],
    ),
    "orientation": (
        "Orientation",
        "Which way phones show the app.",
        [("any", "Any (default)"), ("portrait", "Portrait"), ("landscape", "Landscape")],
    ),
}  # fmt: skip


def build(revision):
    """The manifest for a published revision, as a dict ready for JSON."""
    snapshot = revision.snapshot
    settings = snapshot.get("settings", {})
    app = settings.get("app", {})
    name = app.get("name") or settings.get("site_name") or "Website"
    start_url = app.get("start_url") or "/"
    default_mode = mode_settings(revision)[0]
    scheme = "dark" if default_mode == "dark" else "light"
    background = to_hex(effective_values(snapshot, scheme)["--color-base-100"], alpha=False)
    manifest = {
        "id": start_url,
        "name": name,
        "short_name": app.get("short_name") or name[:12],
        "start_url": start_url,
        "scope": "/",
        "display": app.get("display", "standalone"),
        "background_color": background,
        "theme_color": background,
        "icons": _icons(icon_urls(snapshot)),
    }
    description = app.get("description") or settings.get("tagline")
    if description:
        manifest["description"] = description
    if app.get("orientation", "any") != "any":
        manifest["orientation"] = app["orientation"]
    return manifest


def _icons(urls):
    if not urls:
        return []
    return [
        {"src": urls["icon-192.png"], "sizes": "192x192", "type": "image/png"},
        {"src": urls["icon-512.png"], "sizes": "512x512", "type": "image/png"},
        {
            "src": urls["icon-maskable-512.png"],
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable",
        },
        {
            "src": urls["icon-monochrome-512.png"],
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "monochrome",
        },
    ]
