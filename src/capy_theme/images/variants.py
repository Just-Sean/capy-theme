"""Smaller copies of header logos (AVIF, WebP, PNG or JPEG)."""

import io
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image

from .logos import HEADER_SLOTS

# Steps about 25% apart, so a phone's logo (32 px high) and a desktop's (40 px)
# usually get different files.
WIDTHS = (64, 80, 96, 128, 160, 192, 240, 288, 360, 480, 640, 800, 960, 1280)


MAX_WIDTH = 2560


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
