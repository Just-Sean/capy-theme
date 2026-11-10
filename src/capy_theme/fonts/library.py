"""Font roles and stacks, and copying a theme's chosen fonts into revisions."""

import json
from pathlib import Path

from django.core.files.storage import default_storage

ROLES = {
    "body": "Body text",
    "heading": "Headings",
    "mono": "Monospace (code)",
    "display": "Display (large titles)",
}


DEFAULT_FALLBACK = {
    "body": "ui-sans-serif, system-ui, sans-serif",
    "heading": "ui-sans-serif, system-ui, sans-serif",
    "display": "ui-sans-serif, system-ui, sans-serif",
    "mono": 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace',
}


# System font stacks, from system_stacks.json: [(family, font-family list)].
SYSTEM_STACKS = [
    (entry["family"], entry["stack"])
    for entry in json.loads(
        Path(__file__).with_name("system_stacks.json").read_text(encoding="utf-8")
    )["stacks"]
]


def resolve(font):
    """Return everything the stylesheet needs about a font, as plain data."""
    return {
        "id": font.pk,
        "family": font.family,
        "source": font.source,
        "fallback": font.fallback_stack,
        "stylesheet": font.stylesheet_url,
        "files": [
            {
                "url": file_url(f.file.name),
                "weight": f.weight,
                "style": f.style,
                "subset": f.subset,
                "unicode_range": f.unicode_range,
            }
            for f in font.files.all()
        ],
    }


def file_url(name):
    return default_storage.url(name)


def snapshot_fonts(settings):
    """Return {role: resolved font} for the fonts a theme's settings choose."""
    from .models import Font

    chosen = settings.get("fonts", {})
    fonts = {f.pk: f for f in Font.objects.filter(pk__in=chosen.values()).prefetch_related("files")}
    return {role: resolve(fonts[pk]) for role, pk in chosen.items() if pk in fonts}


def stack(role, font):
    """The font-family value for a role: the font, then its fallbacks."""
    family = font["family"].replace('"', "")
    if font["source"] == "system":
        return font["fallback"] or DEFAULT_FALLBACK[role]
    return f'"{family}", {font["fallback"] or DEFAULT_FALLBACK[role]}'


def preview_stack(font):
    """A font-family value for showing a sample of a library font."""
    if font.source == "system":
        return font.fallback_stack or DEFAULT_FALLBACK["body"]
    family = font.family.replace('"', "")
    return f'"{family}", {font.fallback_stack or DEFAULT_FALLBACK["body"]}'


def preview_faces(font):
    """@font-face rules for a library font's regular file, for previews."""
    files = [f for f in font.files.all() if f.style == "normal"] or list(font.files.all())
    family = font.family.replace('"', "")
    return "".join(
        f'@font-face{{font-family:"{family}";src:url("{file_url(f.file.name)}") format("woff2");'
        f"font-weight:{f.weight};font-style:{f.style};font-display:swap}}"
        for f in files
    )


def external_stylesheets(fonts):
    """The external stylesheet URLs a snapshot's fonts need, in role order, no repeats."""
    urls = []
    for font in (fonts or {}).values():
        url = font.get("stylesheet")
        if font.get("source") == "external" and url and url not in urls:
            urls.append(url)
    return urls


def preload_urls(fonts):
    """The body and heading fonts' regular files, to preload in <head>.

    One file per role (Latin, weight 400, normal style if there is one), no
    repeats, so text appears in the right font sooner.
    """
    urls = []
    for role in ("body", "heading"):
        font = (fonts or {}).get(role)
        if not font or not font.get("files"):
            continue
        files = font["files"]
        best = sorted(
            files,
            key=lambda f: (
                f["style"] != "normal",
                abs(f["weight"] - 400),
                f["subset"] not in ("latin", "all"),
            ),
        )[0]
        if best["url"] not in urls:
            urls.append(best["url"])
    return urls
