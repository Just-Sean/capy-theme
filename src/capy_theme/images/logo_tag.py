"""The HTML and CSS for a theme's logo: <picture> and srcset.

Used by the live editor's header (editor.live_edit_view.draft_header); the logo URLs are
also exposed as data in the theme's assets (``get_artifacts``), for a consumer to render.
"""

from django.utils.html import format_html, format_html_join

from ..storage import theme_storage
from .logos import HEADER_SLOTS, HEIGHTS, MOBILE, resolve


def logo_html(snapshot, slot, alt, attrs, marker=None):
    """A <picture> (or <img>) for the slot, or "" if no image.

    `marker` attributes go on the outermost element (the live editor's, so it can
    swap the logo in a preview, #271).
    """
    image = resolve(snapshot, slot)
    if image is None:
        return ""
    # Email and print logos are a plain <img>: email programs don't handle
    # <picture> or srcset.
    if slot not in HEADER_SLOTS:
        image = {**image, "variants": []}
    heights = _heights(snapshot)
    marker = marker or {}
    return _picture(image, slot, alt, attrs, heights, "", lazy=False, marker=marker)


def _heights(snapshot):
    chosen = snapshot.get("settings", {}).get("logo", {})
    return {name: chosen.get(name, default) for name, (_label, default) in HEIGHTS.items()}


def _picture(image, slot, alt, attrs, heights, mode_class, lazy, marker):
    url = theme_storage().url
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
        if marker:
            img_attrs.update(marker)
            return format_html(
                '<img src="{}" alt="{}"{}>',
                url(image["file"]),
                image.get("alt") or alt,
                format_html_join("", ' {}="{}"', sorted(img_attrs.items())),
            )
        return img
    return format_html(
        "<picture{}{}>{}{}</picture>",
        format_html(' class="{}"', mode_class) if mode_class else "",
        format_html_join("", ' {}="{}"', sorted(marker.items())),
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
    """CSS for header logo heights (in @layer base, so a project's utility
    classes still win)."""
    heights = _heights(snapshot)
    return "\n".join(
        [
            "@layer base {",
            f"  :root img.capy-logo {{ height: {heights['header_height']}px; width: auto; }}",
            f"  @media (max-width: {MOBILE}px) {{",
            f"    :root img.capy-logo {{ height: {heights['header_height_mobile']}px; }}",
            "  }",
            "}",
        ]
    )
