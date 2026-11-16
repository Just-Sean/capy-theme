"""Font roles and stacks, and copying a theme's chosen fonts into revisions."""

import json
import re
from pathlib import Path

from django.core.files.storage import default_storage

from .models import FALLBACK_PATTERN, UNICODE_RANGE_PATTERN

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
                "file": f.file.name,  # the URL is built when used (#254)
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


def font_file_url(entry):
    """The URL of one font file in a snapshot.

    Revisions store the file's name, so a new MEDIA_URL or CDN applies to them
    too; revisions published before 1.0 stored the URL itself (#254).
    """
    return file_url(entry["file"]) if "file" in entry else entry["url"]


def snapshot_fonts(settings):
    """Return {role: resolved font} for the fonts a theme's settings choose."""
    from .models import Font

    chosen = settings.get("fonts", {})
    fonts = {f.pk: f for f in Font.objects.filter(pk__in=chosen.values()).prefetch_related("files")}
    return {role: resolve(fonts[pk]) for role, pk in chosen.items() if pk in fonts}


def safe_fallback(value, role):
    """A fallback stack that's safe in CSS, or the role's default.

    Values are checked when saved (#235), but revisions and fonts saved before that
    may hold anything, so CSS output checks again.
    """
    if value and re.match(FALLBACK_PATTERN, value):
        return value
    return DEFAULT_FALLBACK[role]


def safe_unicode_range(value):
    """A unicode-range value that's safe in CSS, or "" (all characters)."""
    return value if value and re.match(UNICODE_RANGE_PATTERN, value) else ""


def stack(role, font):
    """The font-family value for a role: the font, then its fallbacks."""
    fallback = safe_fallback(font["fallback"], role)
    if font["source"] == "system":
        return fallback
    return f"{css_string(font['family'])}, {fallback}"


def preview_stack(font):
    """A font-family value for showing a sample of a library font."""
    fallback = safe_fallback(font.fallback_stack, "body")
    if font.source == "system":
        return fallback
    return f"{css_string(font.family)}, {fallback}"


CSS_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_.:/?=&%~+,@#!$*")


def css_string(value):
    """`value` as a quoted CSS string that can't end the string, a rule or a <style> block.

    Letters, digits and URL punctuation stay as they are; anything else becomes a
    CSS escape (e.g. < becomes \\3c), which CSS reads back as the same character.
    """
    return '"' + "".join(c if c in CSS_SAFE else f"\\{ord(c):x} " for c in str(value)) + '"'


def preview_faces(font):
    """@font-face rules for a library font's regular file, for previews.

    Every value from the font's data goes through css_string() or int(), so the
    result is safe inside the admin's <style> block (#235).
    """
    files = [f for f in font.files.all() if f.style == "normal"] or list(font.files.all())
    family = css_string(font.family)
    return "".join(
        f"@font-face{{font-family:{family};src:url({css_string(file_url(f.file.name))}) "
        f'format("woff2");font-weight:{int(f.weight)};'
        f"font-style:{'italic' if f.style == 'italic' else 'normal'};font-display:swap}}"
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
        best_url = font_file_url(best)
        if best_url not in urls:
            urls.append(best_url)
    return urls
