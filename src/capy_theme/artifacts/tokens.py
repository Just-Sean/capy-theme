"""The theme as W3C design tokens (Design Tokens Format Module 2025.10).

Design tools (Figma, Tokens Studio, Style Dictionary...) and native app builds
read this format. It's made from the same data as the JSON API (get_artifacts),
so the two always agree. Every token states its $type, so validators check
every value.
"""

import math
import re

from coloraide import Color

FORMAT = "https://www.designtokens.org/TR/2025.10/format/"
_DIMENSION = re.compile(r"^(-?\d+(?:\.\d+)?)(px|rem)$")


def build_tokens(artifacts):
    """The design tokens for get_artifacts() data, as a dict ready for JSON."""
    tokens = {
        "$description": f"{artifacts['theme']['name']} (revision "
        f"{artifacts['theme']['revision']}), exported by capy-theme. Format: {FORMAT}",
    }
    for mode in ("light", "dark"):
        tokens[mode] = {
            "$description": f"Values in {mode} mode.",
            "color": {
                name: _color(value, artifacts["colors_hex"][mode][name])
                for name, value in artifacts["colors"][mode].items()
            },
            "shape": {
                name.replace("_", "-"): _shape(value)
                for name, value in artifacts["shape"][mode].items()
            },
        }
    fonts = {
        role: {"$type": "fontFamily", "$value": _families(font["stack"])}
        for role, font in artifacts["fonts"].items()
    }
    if fonts:
        tokens["font"] = fonts
    type_tokens = _type(artifacts["type"])
    if type_tokens:
        tokens["type"] = type_tokens
    return tokens


def _color(value, hex_value):
    # normalize(): a colour without chroma has no hue (NaN), written as "none".
    lightness, chroma, hue = Color(value).convert("oklch").normalize().coords()
    components = [_round(lightness), _round(chroma), "none" if math.isnan(hue) else _round(hue)]
    alpha = Color(value).alpha()
    # hex: the 6-digit sRGB fallback the format allows (from colors_hex).
    token_value = {"colorSpace": "oklch", "components": components, "hex": hex_value}
    if alpha < 1:
        token_value["alpha"] = _round(alpha)
    return {"$type": "color", "$value": token_value}


def _shape(css):
    match = _DIMENSION.match(css.strip())
    if match:
        return {
            "$type": "dimension",
            "$value": {"value": _round(float(match.group(1))), "unit": match.group(2)},
        }
    return {"$type": "number", "$value": _round(float(css))}  # depth and noise: 0 or 1


def _families(stack):
    """A CSS font-family list as an array of names, without quotes."""
    return [name.strip().strip("\"'") for name in stack.split(",") if name.strip()]


def _type(settings):
    tokens = {}
    if "base_size" in settings:
        tokens["base-size"] = {
            "$type": "dimension",
            "$value": {"value": settings["base_size"], "unit": "px"},
        }
    for name in ("scale", "line_height"):
        if name in settings:
            tokens[name.replace("_", "-")] = {"$type": "number", "$value": settings[name]}
    if "heading_weight" in settings:
        tokens["heading-weight"] = {"$type": "fontWeight", "$value": settings["heading_weight"]}
    return tokens


def _round(number):
    return round(number, 6)
