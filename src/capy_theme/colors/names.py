"""The 20 daisyUI colours: names, groups and labels, and a theme's overrides."""

# The 20 colours, grouped as the admin shows them. Each name is the CSS
# variable without its "--color-" prefix.
COLOR_GROUPS = {
    "Basic": ["primary", "secondary", "accent", "neutral", "base-100", "base-content"],
    "Advanced": ["info", "success", "warning", "error", "base-200", "base-300"],
    "Expert": [
        "primary-content",
        "secondary-content",
        "accent-content",
        "neutral-content",
        "info-content",
        "success-content",
        "warning-content",
        "error-content",
    ],
}


COLOR_NAMES = [name for names in COLOR_GROUPS.values() for name in names]


SCHEMES = ("light", "dark")


COLOR_LABELS = {
    "base-100": "Background",
    "base-200": "Background, darker",
    "base-300": "Background, darkest",
    "base-content": "Text on background",
}


def label(name):
    """A readable label for a colour, e.g. "Primary text" for primary-content."""
    if name in COLOR_LABELS:
        return COLOR_LABELS[name]
    if name.endswith("-content"):
        return f"{name.removesuffix('-content').capitalize()} text"
    return name.capitalize()


def overrides(settings, scheme):
    """Return {name: value} of a scheme's overridden colours from theme settings."""
    return dict(settings.get("colors", {}).get(scheme, {}))


# Colours that have a matching "-content" (text) colour.
WITH_CONTENT = [
    "primary",
    "secondary",
    "accent",
    "neutral",
    "info",
    "success",
    "warning",
    "error",
]
