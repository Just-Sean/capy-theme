"""The 20 daisyUI colours a theme can override, separately for light and dark.

Overrides live in Theme.settings["colors"]["light" | "dark"][name], e.g.
settings["colors"]["light"]["primary"] = "oklch(62% 0.19 260)". Anything not
overridden comes from the base theme.
"""

from coloraide import Color

from .shape import shape_values

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


def effective_values(snapshot, scheme):
    """Return a published revision's CSS values for one scheme.

    The base theme's values, with the theme's shape and colour overrides on top. When a
    colour is overridden but its text colour isn't, the text colour is worked
    out so it's readable. When the background (base-100) is overridden but its
    shades or text aren't, those are worked out from it too.
    """
    values = dict(snapshot[f"{scheme}_values"])
    values.update(shape_values(snapshot.get("settings", {})))
    chosen = overrides(snapshot.get("settings", {}), scheme)
    for name, value in chosen.items():
        values[f"--color-{name}"] = value
    for name in WITH_CONTENT:
        if name in chosen and f"{name}-content" not in chosen:
            values[f"--color-{name}-content"] = readable_text(chosen[name])
    if "base-100" in chosen:
        background = chosen["base-100"]
        if "base-200" not in chosen:
            values["--color-base-200"] = shade(background, 1)
        if "base-300" not in chosen:
            values["--color-base-300"] = shade(background, 2)
        if "base-content" not in chosen:
            values["--color-base-content"] = readable_text(background)
    return values


def contrast(foreground, background):
    """Return the WCAG 2 contrast ratio between two colours (1 to 21)."""
    return Color(foreground).contrast(Color(background), method="wcag21")


def readable_text(background):
    """Return a text colour that reads well on `background`.

    Prefers a very light or very dark tint of the background's own hue, which
    looks better than plain white or black. If neither tint reaches WCAG AA
    (4.5:1), uses pure white or black instead, which is the most any colour
    can get on a mid-tone background.
    """
    lightness, chroma, hue = Color(background).convert("oklch").coords(nans=False)
    tints = [_oklch(0.98, min(chroma, 0.02), hue), _oklch(0.22, min(chroma, 0.05), hue)]
    best = max(tints, key=lambda text: contrast(text, background))
    if contrast(best, background) >= AA:
        return best
    return max(["oklch(100% 0 0)", "oklch(0% 0 0)"], key=lambda text: contrast(text, background))


AA = 4.5  # WCAG 2 minimum contrast for normal text
AAA = 7.0  # WCAG 2 enhanced contrast for normal text


def shade(background, step):
    """Return a slightly darker shade of a background (step 1 or 2), as daisyUI does.

    Very dark backgrounds get lighter shades instead, so the shades stay visible.
    """
    color = Color(background).convert("oklch")
    lightness, chroma, hue = color.coords(nans=False)
    change = 0.025 * step
    lightness = lightness - change if lightness - change >= 0.05 else lightness + change
    return _oklch(lightness, chroma, hue, color.alpha(nans=False))


def _oklch(lightness, chroma, hue, alpha=1):
    text = f"oklch({_number(lightness * 100, 2)}% {_number(chroma, 4)} {_number(hue, 2)}"
    return text + (f" / {_number(alpha, 3)})" if alpha < 1 else ")")


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
    return _oklch(lightness, chroma, hue, color.alpha(nans=False))


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


# The colour pairs WCAG ratings are given for: (background, text on it).
CONTRAST_PAIRS = [(name, f"{name}-content") for name in WITH_CONTENT] + [
    ("base-100", "base-content"),
    ("base-200", "base-content"),
    ("base-300", "base-content"),
]


def rating(ratio):
    """Return "AAA", "AA" or "fail" for a WCAG 2 contrast ratio (normal-size text)."""
    if ratio >= AAA:
        return "AAA"
    if ratio >= AA:
        return "AA"
    return "fail"


def contrast_report(values):
    """Return one entry per colour pair: background, text, ratio and rating.

    `values` are a scheme's CSS values (from effective_values). Ratings are
    warnings only; they never stop a theme being saved or published.
    """
    report = []
    for background, text in CONTRAST_PAIRS:
        ratio = contrast(values[f"--color-{text}"], values[f"--color-{background}"])
        report.append(
            {
                "background": background,
                "text": text,
                "ratio": round(ratio, 2),
                "rating": rating(ratio),
            }
        )
    return report


def draft_values(theme, scheme):
    """Return the CSS values a theme's draft would publish for one scheme.

    Uses the same merging as publishing. Empty if a base no longer exists.
    """
    snapshot = theme.snapshot()
    if snapshot.get(f"{scheme}_values") is None:
        return {}
    return effective_values(snapshot, scheme)
