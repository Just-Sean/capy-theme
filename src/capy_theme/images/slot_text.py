"""How each image slot is described to people, in the admin and the live editor."""

from .logos import FALLBACK
from .slots import NO_SVG, SLOTS
from .uploads import byte_limit


def limits_text(slot):
    """E.g. "Up to 2 MB and 4000 px, PNG, JPEG, WebP, GIF or SVG." """
    size = byte_limit(slot)
    amount = f"{size // (1024 * 1024)} MB" if size >= 1024 * 1024 else f"{size // 1024} KB"
    kinds = "PNG, JPEG, WebP or GIF" if slot in NO_SVG else "PNG, JPEG, WebP, GIF or SVG"
    return f"Up to {amount} and {SLOTS[slot][2]} px, {kinds}."


def help_text(slot, mode):
    """What the slot is for and its limits (light), or what dark mode does (dark)."""
    if mode == "dark":
        return "The version for dark mode. Leave it empty to use the light image in dark mode too."
    return f"{SLOTS[slot][3]} {limits_text(slot)}"


def empty_text(slot, mode):
    """What a slot with no image shows."""
    if mode == "dark":
        return "No dark image: the light one is used in dark mode too."
    if slot == "logo_main":
        return "No image: the site name is shown instead."
    if slot in FALLBACK:
        return "No image: the main logo is used."
    return "No image."
