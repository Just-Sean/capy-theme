"""The HTML and CSS for {% theme_logo %}: <picture>, srcset and light/dark switching."""

from django.core.files.storage import default_storage
from django.utils.html import format_html, format_html_join

from .logos import HEADER_SLOTS, HEIGHTS, MOBILE, resolve


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
