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


def images(revision):
    """Data for the showcase's images section, per mode.

    {mode: {"logos": [...], "icons": [...], "backgrounds": [...]}, plus
    "preview" (the link-preview card) and "manifest" (the manifest's values)}.
    Each logo says which image it shows and why (its own, the light one, or the
    main logo it falls back to).
    """
    from django.core.files.storage import default_storage

    from .icons import FILES, icon_urls
    from .images import SLOTS
    from .logos import FALLBACK, HEADER_SLOTS, LOGO_SLOTS, resolve
    from .manifest import build as build_manifest
    from .social import SIZE, sharing_image

    if revision is None:
        return None
    snapshot = revision.snapshot
    settings = snapshot.get("settings", {})
    chosen = snapshot.get("images", {})
    url = default_storage.url
    result = {}
    for mode in SCHEMES:
        logos = []
        for slot in LOGO_SLOTS:
            # Email and print logos always use the light version (see logos.logo_html).
            header = slot in HEADER_SLOTS
            image = resolve(snapshot, slot, mode if header else "light")
            own = chosen.get(slot, {})
            if not header and mode == "dark" and image:
                source = "Always the light version (emails and print have no dark mode)"
            elif mode in own:
                source = "Its own image"
            elif "light" in own:
                source = "No dark version: uses the light one"
            elif FALLBACK.get(slot) and image:
                source = f"Empty: falls back to the {SLOTS[FALLBACK[slot]][0].lower()}"
            elif image:
                source = "From before logo slots"
            else:
                source = "Empty: shows the site name"
            # Email and print logos are always the plain file (see logos.logo_html).
            variants = image.get("variants", []) if image and slot in HEADER_SLOTS else []
            logos.append(
                {
                    "slot": slot,
                    "label": SLOTS[slot][0],
                    "header": slot in HEADER_SLOTS,
                    "url": url(image["file"]) if image else "",
                    "width": image["width"] if image else 0,
                    "height": image["height"] if image else 0,
                    "alt": (image or {}).get("alt") or settings.get("site_name", ""),
                    "source": source,
                    "formats": sorted({v["format"].upper() for v in variants}),
                    "widths": sorted({v["width"] for v in variants}),
                }
            )
        backgrounds = [
            {
                "label": SLOTS[slot][0],
                "class": f"capy-bg-{slot.removeprefix('background_')}",
                "set": resolve(snapshot, slot, mode) is not None,
            }
            for slot in ("background_login", "background_pattern")
        ]
        result[mode] = {"logos": logos, "backgrounds": backgrounds}
    urls = icon_urls(snapshot)
    result["icons"] = (
        [
            {"name": name, "url": urls[name], "size": size, "label": text}
            for name, (size, text) in FILES.items()
        ]
        if urls
        else []
    )
    share = sharing_image(snapshot)
    result["preview"] = {
        "image": url(share["file"]) if share else "",
        "alt": share["alt"] if share else "",
        "size": SIZE,
        "title": settings.get("site_name", ""),
        "description": settings.get("social", {}).get("description") or settings.get("tagline", ""),
    }
    manifest = build_manifest(revision)
    result["manifest"] = [(key, value) for key, value in manifest.items() if key != "icons"] + [
        ("icons", f"{len(manifest['icons'])} icons")
    ]
    return result
