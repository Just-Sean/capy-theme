"""Exporting a theme as one zip: theme.json plus its image and font files.

theme.json holds the draft (bases and settings). Its fonts and images are given
keys ("font-3", "image-12"), because database ids differ between sites; the
import maps them to new ids. Generated files (logo copies, icons) aren't
included: the import and the next publish make them again.
"""

import io
import json
import zipfile
from importlib.metadata import version
from pathlib import Path

from ..fonts.models import Font

FORMAT = "capy-theme-export/1"


def export_theme(theme):
    """The theme as zip bytes (see the module docstring)."""
    settings = json.loads(json.dumps(theme.settings))
    font_roles = {role: f"font-{pk}" for role, pk in settings.pop("fonts", {}).items()}
    image_slots = {
        slot: {mode: f"image-{pk}" for mode, pk in modes.items()}
        for slot, modes in settings.pop("images", {}).items()
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        fonts = _fonts(archive, {int(key.split("-")[1]) for key in font_roles.values()})
        images = _images(archive, theme, image_slots)
        manifest = {
            "format": FORMAT,
            "exported_by": f"capy-theme {version('capy-theme')}",
            "theme": {
                "name": theme.name,
                "slug": theme.slug,
                "light_base": theme.light_base,
                "dark_base": theme.dark_base,
                "settings": settings,
                "font_roles": font_roles,
                "image_slots": image_slots,
            },
            "fonts": fonts,
            "images": images,
        }
        archive.writestr("theme.json", json.dumps(manifest, indent=2, ensure_ascii=False))
    return buffer.getvalue()


def _fonts(archive, ids):
    fonts = {}
    for font in Font.objects.filter(pk__in=ids).prefetch_related("files"):
        files = []
        for index, font_file in enumerate(font.files.all()):
            path = f"fonts/{font.pk}-{index}.woff2"
            with font_file.file.open("rb") as handle:
                archive.writestr(path, handle.read())
            files.append(
                {
                    "path": path,
                    "weight": font_file.weight,
                    "style": font_file.style,
                    "subset": font_file.subset,
                    "unicode_range": font_file.unicode_range,
                }
            )
        fonts[f"font-{font.pk}"] = {
            "family": font.family,
            "source": font.source,
            "fallback_stack": font.fallback_stack,
            "licence": font.licence,
            "stylesheet_url": font.stylesheet_url,
            "files": files,
        }
    return fonts


def _images(archive, theme, image_slots):
    keys = {key for modes in image_slots.values() for key in modes.values()}
    images = {}
    for asset in theme.assets.filter(pk__in=[int(key.split("-")[1]) for key in keys]):
        # Keeps the file's name (storage names only use letters, digits, - _ and .).
        name = Path(asset.original.name)
        path = f"images/{asset.pk}-{name.stem[:100]}{name.suffix.lower()}"
        with asset.original.open("rb") as handle:
            archive.writestr(path, handle.read())
        images[f"image-{asset.pk}"] = {
            "slot": asset.slot,
            "mode": asset.mode,
            "alt_text": asset.alt_text,
            "path": path,
        }
    return images
