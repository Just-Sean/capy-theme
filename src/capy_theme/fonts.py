"""Fonts: the four roles a theme can set, and the CSS that applies them.

A theme picks fonts from the shared library by id, in settings["fonts"], e.g.
{"heading": 3}. When a theme is published, each chosen font is copied into the
revision (family, fallback stack and file URLs), so later changes to the library
can't change a published theme.
"""

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


def font_css(fonts):
    """Return CSS lines for a snapshot's fonts: @font-face rules, variables and rules.

    - Body sets Tailwind's --font-sans (and body's font), mono sets --font-mono.
    - Headings and display get --capy-font-heading / --capy-font-display, used by
      h1–h6 and the .capy-display class.
    Element rules are in @layer base, so a project's own utility classes still win.
    """
    if not fonts:
        return []
    lines = []
    seen = set()
    for font in fonts.values():
        for f in font["files"]:
            # The same file can serve several weights (variable fonts), so each
            # weight and style still gets its own rule; only exact repeats are skipped.
            key = (font["family"], f["url"], f["weight"], f["style"], f["unicode_range"])
            if key in seen:
                continue
            seen.add(key)
            lines += [
                "@font-face {",
                f'  font-family: "{font["family"].replace(chr(34), "")}";',
                f'  src: url("{f["url"]}") format("woff2");',
                f"  font-weight: {f['weight']};",
                f"  font-style: {f['style']};",
                "  font-display: swap;",
            ]
            if f["unicode_range"]:
                lines.append(f"  unicode-range: {f['unicode_range']};")
            lines.append("}")
    variables = {
        "body": ["--font-sans", "--capy-font-body"],
        "mono": ["--font-mono", "--capy-font-mono"],
        "heading": ["--capy-font-heading"],
        "display": ["--capy-font-display"],
    }
    lines.append(":root {")
    for role, font in fonts.items():
        for variable in variables.get(role, []):
            lines.append(f"  {variable}: {stack(role, font)};")
    lines.append("}")
    lines.append("@layer base {")
    if "body" in fonts:
        lines.append("  body { font-family: var(--capy-font-body); }")
    if "heading" in fonts:
        lines.append("  h1, h2, h3, h4, h5, h6 { font-family: var(--capy-font-heading); }")
    if "mono" in fonts:
        lines.append("  code, kbd, samp, pre { font-family: var(--capy-font-mono); }")
    if "display" in fonts:
        lines.append("  .capy-display { font-family: var(--capy-font-display); }")
    lines.append("}")
    return lines


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
