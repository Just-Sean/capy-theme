"""The image slots (logos, icon, sharing image, backgrounds), their limits and modes."""

MB = 1024 * 1024


# slot: (label, max bytes, max width or height in pixels, help)
SLOTS = {
    "logo_main": ("Main logo", 2 * MB, 4000, "The logo in the site header."),
    "logo_stacked": ("Stacked logo", 2 * MB, 4000, "Mark above the name, for narrow spaces."),
    "logo_mark": ("Logo mark", 2 * MB, 4000, "The symbol on its own."),
    "logo_wordmark": ("Wordmark", 2 * MB, 4000, "The name on its own."),
    "logo_email": ("Email logo", 1 * MB, 2000, "For HTML emails (PNG is safest)."),
    "logo_print": ("Print logo", 5 * MB, 6000, "High resolution, for print."),
    "icon": ("Icon", 2 * MB, 4000, "One square image: favicons and app icons are made from it."),
    "social": (
        "Social sharing image",
        5 * MB,
        6000,
        "Shown in link previews (cropped to 1200 × 630).",
    ),
    "background_login": ("Login background", 5 * MB, 6000, "Behind the login page."),
    "background_pattern": (
        "Page background pattern",
        2 * MB,
        4000,
        "A tiling pattern behind pages.",
    ),
}


# Slots where SVG can't be used, so a PNG, JPEG, WebP or GIF must be uploaded:
# email clients (Gmail, Outlook) don't show SVG, social sites don't accept it for
# link previews, and favicons and app icons are made from the icon with Pillow.
NO_SVG = {
    "logo_email": "Email programs don't show SVG",
    "social": "Social sites don't accept SVG for link previews",
    "icon": "Favicons and app icons are made from it as PNGs",
}


SLOT_CHOICES = [(slot, spec[0]) for slot, spec in SLOTS.items()]


MODES = [("light", "Light"), ("dark", "Dark")]
