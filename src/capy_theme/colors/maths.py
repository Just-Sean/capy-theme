"""Colour maths: OKLCH conversion, WCAG contrast, readable text colours and shades."""

from coloraide import Color

from .names import COLOR_NAMES


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


def rating(ratio):
    """Return "AAA", "AA" or "fail" for a WCAG 2 contrast ratio (normal-size text)."""
    if ratio >= AAA:
        return "AAA"
    if ratio >= AA:
        return "AA"
    return "fail"


NON_TEXT = 3.0  # WCAG 2 minimum contrast for focus outlines and other non-text parts


def focus_color(values):
    """Return a focus-outline colour that stays visible on the page background.

    The primary colour if it has at least 3:1 contrast with the background
    (WCAG's minimum for non-text parts), otherwise the text colour.
    """
    background = values["--color-base-100"]
    primary = values["--color-primary"]
    return primary if contrast(primary, background) >= NON_TEXT else values["--color-base-content"]


def hex_colors(values):
    """Return every colour as #rrggbb, keyed like "primary" or "base_100".

    For HTML emails, which can't use OKLCH or CSS variables.
    """
    return {
        name.replace("-", "_"): to_hex(values[f"--color-{name}"], alpha=False)
        for name in COLOR_NAMES
    }
