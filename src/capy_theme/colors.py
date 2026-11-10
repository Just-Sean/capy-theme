"""The 20 daisyUI colours a theme can override, separately for light and dark.

Overrides live in Theme.settings["colors"]["light" | "dark"][name], e.g.
settings["colors"]["light"]["primary"] = "oklch(62% 0.19 260)". Anything not
overridden comes from the base theme.
"""

from coloraide import Color

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


def effective_values(snapshot, scheme):
    """Return a published revision's CSS values for one scheme.

    The base theme's values, with the theme's colour overrides on top.
    """
    values = dict(snapshot[f"{scheme}_values"])
    for name, value in overrides(snapshot.get("settings", {}), scheme).items():
        values[f"--color-{name}"] = value
    return values


def to_oklch(value):
    """Return a colour written any common way as daisyUI-style OKLCH text.

    Accepts hex (#3b82f6), rgb(), hsl(), oklch() and colour names. Raises
    ValueError if it isn't a colour. Example: "#3b82f6" -> "oklch(62.31% 0.188 259.81)".
    """
    try:
        color = Color(value.strip()).convert("oklch")
    except (ValueError, TypeError, AttributeError) as error:
        raise ValueError(f"{value!r} isn't a colour") from error
    lightness, chroma, hue = color.coords(nans=False)
    alpha = color.alpha(nans=False)
    text = f"oklch({_number(lightness * 100, 2)}% {_number(chroma, 4)} {_number(hue, 2)}"
    return text + (f" / {_number(alpha, 3)})" if alpha < 1 else ")")


def to_hex(value, alpha=None):
    """Return an OKLCH (or any CSS) colour as #rrggbb, fitted into sRGB.

    Transparency is added (#rrggbbaa) only when the colour has some. With
    alpha=False it's always dropped (the browser's colour input needs that).
    """
    return Color(value).convert("srgb").to_string(hex=True, fit=True, alpha=alpha)


def _number(value, places):
    """Round and drop trailing zeros: 62.300 -> "62.3", 260.0 -> "260"."""
    text = f"{round(value, places):.{places}f}".rstrip("0").rstrip(".")
    return text if text not in ("-0", "") else "0"
