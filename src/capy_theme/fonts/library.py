"""Font roles and stacks, and copying a theme's chosen fonts into revisions."""

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


# Ready-made stacks of fonts already on visitors' devices: nothing to download.
# Added to the font library by migration 0008. Most come from Modern Font Stacks
# (https://modernfontstacks.com, CC0).
SYSTEM_STACKS = [
    ("System sans", "ui-sans-serif, system-ui, sans-serif"),
    ("System serif", 'ui-serif, Georgia, Cambria, "Times New Roman", Times, serif'),
    ("System mono", 'ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace'),
    ("Transitional", 'Charter, "Bitstream Charter", "Sitka Text", Cambria, serif'),
    ("Old Style", '"Iowan Old Style", "Palatino Linotype", "URW Palladio L", P052, serif'),
    (
        "Humanist",
        'Seravek, "Gill Sans Nova", Ubuntu, Calibri, "DejaVu Sans", source-sans-pro, sans-serif',
    ),
    (
        "Geometric Humanist",
        'Avenir, Montserrat, Corbel, "URW Gothic", source-sans-pro, sans-serif',
    ),
    (
        "Neo-Grotesque",
        'Inter, Roboto, "Helvetica Neue", "Arial Nova", "Nimbus Sans", Arial, sans-serif',
    ),
    (
        "Rounded",
        'ui-rounded, "Hiragino Maru Gothic ProN", Quicksand, Comfortaa, Manjari, '
        '"Arial Rounded MT", "Arial Rounded MT Bold", Calibri, source-sans-pro, sans-serif',
    ),
    (
        "Slab Serif",
        'Rockwell, "Rockwell Nova", "Roboto Slab", "DejaVu Serif", "Sitka Small", serif',
    ),
    ("Didone", 'Didot, "Bodoni MT", "Noto Serif Display", "URW Palladio L", P052, Sylfaen, serif'),
    (
        "Monospace Code",
        'ui-monospace, "Cascadia Code", "Source Code Pro", Menlo, Consolas, '
        '"DejaVu Sans Mono", monospace',
    ),
    (
        "Industrial",
        'Bahnschrift, "DIN Alternate", "Franklin Gothic Medium", "Nimbus Sans Narrow", '
        "sans-serif-condensed, sans-serif",
    ),
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
