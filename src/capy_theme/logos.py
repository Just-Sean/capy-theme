"""Logo slots: which image each slot uses, its sizes and formats, and the HTML.

A theme chooses an uploaded image (a ThemeAsset) for each slot and mode in
`settings["images"]`, e.g. {"logo_main": {"light": 4, "dark": 7}}. Publishing
copies the chosen images' files and sizes into the revision, so pages never
read the draft.

Images for the header slots get smaller copies in AVIF, WebP and PNG or JPEG,
so browsers download only the size they need.
"""

import io
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.html import format_html, format_html_join
from PIL import Image

LOGO_SLOTS = (
    "logo_main",
    "logo_stacked",
    "logo_mark",
    "logo_wordmark",
    "logo_email",
    "logo_print",
)
# When a slot has no image, the slot it falls back to.
FALLBACK = {slot: "logo_main" for slot in LOGO_SLOTS if slot != "logo_main"}
# Slots shown in page headers: these get smaller copies and the header height.
HEADER_SLOTS = ("logo_main", "logo_stacked", "logo_mark", "logo_wordmark")
# Steps about 25% apart, so a phone's logo (32 px high) and a desktop's (40 px)
# usually get different files.
WIDTHS = (64, 80, 96, 128, 160, 192, 240, 288, 360, 480, 640, 800, 960, 1280)
MAX_WIDTH = 2560
# Header logo heights (px). Phones are windows up to MOBILE px wide.
HEIGHTS = {
    "header_height": ("Header logo height (px)", 40),
    "header_height_mobile": ("Header logo height on phones (px)", 32),
}
MOBILE = 640


def make_variants(asset):
    """Create the smaller copies of a header logo (AVIF, WebP, PNG or JPEG).

    Widths from WIDTHS that are smaller than the image, plus the image's own
    width (at most MAX_WIDTH). Does nothing for SVGs and other slots.
    """
    from .models import ThemeAssetVariant

    if asset.slot not in HEADER_SLOTS or asset.content_type == "image/svg+xml":
        return
    with asset.original.open("rb") as file:
        image = Image.open(file)
        image.load()
    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA")
    fallback = "jpeg" if asset.content_type == "image/jpeg" else "png"
    stem = Path(asset.original.name).stem
    widths = sorted({w for w in WIDTHS if w < asset.width} | {min(asset.width, MAX_WIDTH)})
    for width in widths:
        height = max(1, round(asset.height * width / asset.width))
        resized = image.resize((width, height), Image.Resampling.LANCZOS)
        for fmt in ("avif", "webp", fallback):
            output = io.BytesIO()
            if fmt == "jpeg":
                resized.convert("RGB").save(output, "JPEG", quality=88, optimize=True)
            elif fmt == "png":
                resized.save(output, "PNG", optimize=True)
            elif fmt == "avif":
                resized.save(output, "AVIF", quality=70, speed=8)
            else:
                resized.save(output, "WEBP", quality=85)
            variant = ThemeAssetVariant(asset=asset, width=width, height=height, format=fmt)
            extension = "jpg" if fmt == "jpeg" else fmt
            variant.file.save(
                f"{stem}-{width}w.{extension}", ContentFile(output.getvalue()), save=False
            )
            variant.save()


def snapshot_images(theme, settings):
    """The chosen images, as published: {slot: {mode: {file, width, ...}}}."""
    from .models import ThemeAsset

    chosen = settings.get("images", {})
    ids = {pk for modes in chosen.values() for pk in modes.values()}
    if not ids or theme.pk is None:
        return {}
    assets = {
        a.pk: a
        for a in ThemeAsset.objects.filter(theme=theme, pk__in=ids).prefetch_related("variants")
    }
    images = {}
    for slot, modes in chosen.items():
        for mode, pk in modes.items():
            asset = assets.get(pk)
            if asset is None:
                continue
            images.setdefault(slot, {})[mode] = {
                "file": asset.original.name,
                "width": asset.width,
                "height": asset.height,
                "content_type": asset.content_type,
                "alt": asset.alt_text,
                "variants": [
                    {
                        "file": v.file.name,
                        "width": v.width,
                        "format": v.format,
                        **({"purpose": v.purpose} if v.purpose else {}),
                    }
                    for v in asset.variants.all()
                ],
            }
    return images


def resolve(snapshot, slot, mode):
    """The published image for a slot and mode, following fallbacks, or None.

    Dark mode uses the slot's light image if it has no dark one. A slot with no
    image uses its fallback slot (e.g. the stacked logo falls back to the main one).
    """
    images = snapshot.get("images", {})
    is_logo = slot in LOGO_SLOTS
    while slot:
        entry = images.get(slot, {})
        for choice in (mode, "light") if mode == "dark" else ("light",):
            if choice in entry:
                return entry[choice]
        slot = FALLBACK.get(slot)
    legacy = snapshot.get("logo")  # revisions published before logo slots
    if legacy and is_logo:
        return {"file": legacy, "width": 0, "height": 0, "content_type": "", "alt": ""}
    return None


def logo_html(snapshot, slot, alt, attrs):
    """A <picture> for the slot, with a dark version if there is one. "" if no image.

    With light and dark versions, both are output and the stylesheet shows the one
    for the current mode. Both are loading="lazy", so the browser only downloads
    the one that's shown.
    """
    light = resolve(snapshot, slot, "light")
    if light is None:
        return ""
    # Email and print logos are a plain <img>: email programs don't handle
    # <picture>, srcset or the light/dark CSS.
    if slot not in HEADER_SLOTS:
        light = {**light, "variants": []}
        dark = light
    else:
        dark = resolve(snapshot, slot, "dark")
    heights = _heights(snapshot)
    if dark == light:
        return _picture(light, slot, alt, attrs, heights, "", lazy=False)
    return _picture(light, slot, alt, attrs, heights, "capy-logo-light", lazy=True) + _picture(
        dark, slot, alt, attrs, heights, "capy-logo-dark", lazy=True
    )


def _heights(snapshot):
    chosen = snapshot.get("settings", {}).get("logo", {})
    return {name: chosen.get(name, default) for name, (_label, default) in HEIGHTS.items()}


def _picture(image, slot, alt, attrs, heights, mode_class, lazy):
    url = default_storage.url
    classes = " ".join(
        c for c in ("capy-logo" if slot in HEADER_SLOTS else "", attrs.get("class", "")) if c
    )
    img_attrs = {k: v for k, v in attrs.items() if k != "class"}
    if classes:
        img_attrs["class"] = classes
    if image["width"] and image["height"]:
        img_attrs["width"] = image["width"]
        img_attrs["height"] = image["height"]
    if lazy:
        img_attrs["loading"] = "lazy"
    variants = image.get("variants", [])
    by_format = {}
    for variant in variants:
        by_format.setdefault(variant["format"], []).append(variant)
    sizes = _sizes(image, heights) if variants else ""
    sources = []
    fallback_format = "jpeg" if image["content_type"] == "image/jpeg" else "png"
    for fmt in ("avif", "webp"):
        if fmt in by_format:
            sources.append(
                format_html(
                    '<source type="image/{}" srcset="{}" sizes="{}">',
                    fmt,
                    _srcset(by_format[fmt], url),
                    sizes,
                )
            )
    if fallback_format in by_format:
        img_attrs["srcset"] = _srcset(by_format[fallback_format], url)
        img_attrs["sizes"] = sizes
    img = format_html(
        '<img src="{}" alt="{}"{}>',
        url(image["file"]),
        image.get("alt") or alt,
        format_html_join("", ' {}="{}"', sorted(img_attrs.items())),
    )
    if not sources and not mode_class:
        return img
    return format_html(
        "<picture{}>{}{}</picture>",
        format_html(' class="{}"', mode_class) if mode_class else "",
        format_html_join("", "{}", ((s,) for s in sources)),
        img,
    )


def _srcset(variants, url):
    return ", ".join(f"{url(v['file'])} {v['width']}w" for v in variants)


def _sizes(image, heights):
    """How wide the logo is shown: header height × the image's width/height."""
    ratio = image["width"] / image["height"]
    phone = round(heights["header_height_mobile"] * ratio)
    other = round(heights["header_height"] * ratio)
    return f"(max-width: {MOBILE}px) {phone}px, {other}px"


def logo_css(snapshot):
    """CSS for header logo heights and light/dark switching (in @layer base,
    so a project's utility classes still win)."""
    heights = _heights(snapshot)
    return "\n".join(
        [
            "@layer base {",
            f"  :root img.capy-logo {{ height: {heights['header_height']}px; width: auto; }}",
            f"  @media (max-width: {MOBILE}px) {{",
            f"    :root img.capy-logo {{ height: {heights['header_height_mobile']}px; }}",
            "  }",
            "  :root .capy-logo-dark { display: none; }",
            '  :root[data-theme="capy-dark"] .capy-logo-light { display: none; }',
            '  :root[data-theme="capy-dark"] .capy-logo-dark { display: inline; }',
            "  @media (prefers-color-scheme: dark) {",
            "    :root:not([data-theme]) .capy-logo-light { display: none; }",
            "    :root:not([data-theme]) .capy-logo-dark { display: inline; }",
            "  }",
            "}",
        ]
    )
