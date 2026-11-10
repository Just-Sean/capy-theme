"""Colour suggestions for the editor: from the primary colour, or from the logo.

Suggestions are only ever shown; nothing is saved until the editor's Save.
"""

from coloraide import Color
from PIL import Image

from .colors import _oklch, to_oklch

# name, description, hue shifts for secondary and accent (degrees)
SCHEMES = [
    ("Analogous", "Neighbouring hues: calm and harmonious.", 30, -30),
    ("Complementary", "The opposite hue: strong contrast.", 180, 150),
    ("Triadic", "Three evenly spaced hues: lively and balanced.", 120, 240),
]


def from_primary(primary):
    """Return suggestions of secondary, accent and neutral for a primary colour.

    Secondary and accent keep the primary's lightness and strength and change
    its hue; neutral is a dark, almost grey version of the primary's hue.
    """
    lightness, chroma, hue = Color(to_oklch(primary)).convert("oklch").coords(nans=False)
    neutral = _oklch(0.27, min(chroma, 0.03), hue)
    return [
        {
            "name": name,
            "description": description,
            "colors": {
                "secondary": _oklch(lightness, chroma, (hue + shift_secondary) % 360),
                "accent": _oklch(lightness, chroma, (hue + shift_accent) % 360),
                "neutral": neutral,
            },
        }
        for name, description, shift_secondary, shift_accent in SCHEMES
    ]


def from_logo(file, count=4):
    """Return a suggestion built from a logo's main colours, or None.

    The logo is shrunk and reduced to a few colours. Transparent, near-white and
    near-black pixels are ignored, and the most colourful remaining colours
    become primary, secondary and accent, in order of how much of the logo they
    cover. Neutral is a dark grey of the primary's hue.
    """
    try:
        with Image.open(file) as image:
            image = image.convert("RGBA")
            image.thumbnail((96, 96))
            pixels = [(r, g, b) for r, g, b, a in image.getdata() if a > 128]
    except OSError, ValueError:
        return None
    if not pixels:
        return None
    solid = Image.new("RGB", (len(pixels), 1))
    solid.putdata(pixels)
    reduced = solid.quantize(colors=12)
    palette = reduced.getpalette()
    found = []
    for _amount, index in sorted(reduced.getcolors(), reverse=True):
        r, g, b = palette[index * 3 : index * 3 + 3]
        lightness, chroma, hue = (
            Color("srgb", [r / 255, g / 255, b / 255]).convert("oklch").coords(nans=False)
        )
        if lightness > 0.95 or lightness < 0.12 or chroma < 0.04:
            continue  # background white, outline black or grey: not a brand colour
        if any(abs(hue - h) < 20 or abs(hue - h) > 340 for h, _ in found):
            continue  # too close to a colour already chosen
        found.append((hue, _oklch(lightness, chroma, hue)))
        if len(found) == count - 1:
            break
    if not found:
        return None
    names = ["primary", "secondary", "accent"]
    colors = {names[i]: value for i, (_hue, value) in enumerate(found)}
    colors["neutral"] = _oklch(0.27, 0.02, found[0][0])
    return {
        "name": "From your logo",
        "description": "The logo's main colours, most used first.",
        "colors": colors,
    }
