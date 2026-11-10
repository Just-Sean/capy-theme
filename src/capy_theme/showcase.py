"""Data for the showcase's colour and shape sections."""

from .builtin_themes import THEMES
from .colors import (
    COLOR_NAMES,
    SCHEMES,
    WITH_CONTENT,
    contrast,
    effective_values,
    label,
    overrides,
    rating,
    to_hex,
)
from .shape import EFFECTS, SIZES


def mode_values(revision):
    """Return {mode: CSS values} for a revision, or daisyUI's light/dark defaults."""
    if revision is None:
        return {scheme: dict(THEMES[scheme]["values"]) for scheme in SCHEMES}
    return {scheme: effective_values(revision.snapshot, scheme) for scheme in SCHEMES}


def swatches(revision):
    """Return {mode: [swatch, ...]}: one entry per colour, for the showcase.

    Each swatch has the colour's name, label, OKLCH and hex values, where it
    comes from ("overridden", "worked out" or "base theme"), and, for colours
    with a text colour, the contrast ratio and rating of that pair.
    """
    settings = revision.snapshot.get("settings", {}) if revision else {}
    result = {}
    for scheme, values in mode_values(revision).items():
        chosen = overrides(settings, scheme)
        entries = []
        for name in COLOR_NAMES:
            value = values[f"--color-{name}"]
            entry = {
                "name": name,
                "label": label(name),
                "oklch": value,
                "hex": to_hex(value),
                "source": _source(name, chosen),
                "fg": _foreground(name),
            }
            text = _text_partner(name)
            if text:
                ratio = contrast(values[f"--color-{text}"], value)
                entry |= {"text": text, "ratio": round(ratio, 2), "rating": rating(ratio)}
            entries.append(entry)
        result[scheme] = entries
    return result


def shape_samples(revision):
    """Return {mode: {"sizes": [...], "effects": [...]}} with the current shape values."""
    result = {}
    for scheme, values in mode_values(revision).items():
        result[scheme] = {
            "sizes": [
                {"name": name, "label": spec[4], "variable": spec[0], "value": values[spec[0]]}
                for name, spec in SIZES.items()
            ],
            "effects": [
                {"name": name, "label": spec[1], "variable": spec[0], "on": values[spec[0]] != "0"}
                for name, spec in EFFECTS.items()
            ],
        }
    return result


def _text_partner(name):
    if name in WITH_CONTENT:
        return f"{name}-content"
    if name.startswith("base-") and name != "base-content":
        return "base-content"
    return None


def _foreground(name):
    """The colour to write the swatch's label in: its text colour, or for a text
    colour, the colour it sits on."""
    if name == "base-content":
        return "base-100"
    if name.endswith("-content"):
        return name.removesuffix("-content")
    return _text_partner(name)


def _source(name, chosen):
    if name in chosen:
        return "overridden"
    background = name.removesuffix("-content")
    automatic = (name.endswith("-content") and background in chosen and name != "base-content") or (
        name in ("base-200", "base-300", "base-content") and "base-100" in chosen
    )
    return "worked out" if automatic else "base theme"


SAMPLE_CHARACTERS = {
    "latin": "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz 0123456789 "
    "!?.,:;'\"()[]{}&@#%*+-=/ €£$",
    "latin-ext": "ĀāĂăĆćČčĐđĘęĞğİıŁłŃńŐőŒœŘřŞşŠšŢţŮůŰűŸŹźŽž",
    "cyrillic": "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ абвгдежзийклмнопрстуфхцчшщъыьэюя",
    "cyrillic-ext": "ЀЁЂЃЄЅІЇЈЉЊЋЌЍЎЏ ѐёђѓєѕіїјљњћќѝўџ",
    "greek": "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ αβγδεζηθικλμνξοπρστυφχψω",
    "greek-ext": "ἀἁἂἃἄἅἆἇἐἑἒἓἔἕ",
    "vietnamese": "ẠẢẤẦẨẪẬẮẰẲẴẶ ạảấầẩẫậắằẳẵặ ĂÂĐÊÔƠƯ ăâđêôơư",
}


def typography(revision):
    """The showcase's font and type data: each role's font, weights and the type settings."""
    from .fonts import DEFAULT_FALLBACK, ROLES, stack
    from .typography import heading_sizes

    fonts = (revision.snapshot.get("fonts") if revision else None) or {}
    settings = revision.snapshot.get("settings", {}) if revision else {}
    roles = []
    subsets = {"latin"}
    for role, role_label in ROLES.items():
        font = fonts.get(role)
        if font is None:
            roles.append(
                {"role": role, "label": role_label, "font": None, "stack": DEFAULT_FALLBACK[role]}
            )
            continue
        # Only weights and styles with a real file (or a system/external font's
        # plain regular and bold), so nothing shown is a browser-faked bold.
        faces = sorted({(f["weight"], f["style"]) for f in font["files"]})
        if not faces:
            faces = [(400, "normal"), (700, "normal")]
        subsets.update(f["subset"] for f in font["files"] if f["subset"] in SAMPLE_CHARACTERS)
        roles.append(
            {
                "role": role,
                "label": role_label,
                "font": font,
                "stack": stack(role, font),
                "faces": [{"weight": w, "style": s} for w, s in faces],
                "checked": bool(font["files"]),
            }
        )
    type_settings = settings.get("type", {})
    return {
        "roles": roles,
        "type": type_settings,
        "heading_sizes": heading_sizes(type_settings["scale"])
        if "scale" in type_settings
        else None,
        "characters": [
            (name, SAMPLE_CHARACTERS[name]) for name in SAMPLE_CHARACTERS if name in subsets
        ],
    }
