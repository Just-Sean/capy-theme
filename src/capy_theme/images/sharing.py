"""The sharing image: the theme's image for link previews, at 1200 × 630.

capy-theme only makes the image (and exposes it in artifacts.get_artifacts());
the Open Graph or Twitter tags that use it belong to the project or another module.
"""

import io
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

SIZE = (1200, 630)  # what Facebook, LinkedIn, X and most chat apps show best


def make_sharing_image(asset):
    """Save the asset cropped to 1200 × 630 as a variant (purpose "social").

    Cropped from the centre to fill the whole size. Transparent parts are made
    white, since some sites show transparency as black.
    """
    from .models import ThemeAssetVariant

    with asset.original.open("rb") as file:
        image = Image.open(file)
        image.load()
    image = image.convert("RGBA")
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, image).convert("RGB")
    cropped = ImageOps.fit(flat, SIZE, Image.Resampling.LANCZOS)
    output = io.BytesIO()
    if asset.content_type == "image/jpeg":
        cropped.save(output, "JPEG", quality=88, optimize=True)
        fmt, extension = "jpeg", "jpg"
    else:
        cropped.save(output, "PNG", optimize=True)
        fmt, extension = "png", "png"
    variant = ThemeAssetVariant(
        asset=asset, width=SIZE[0], height=SIZE[1], format=fmt, purpose="social"
    )
    stem = Path(asset.original.name).stem
    variant.file.save(
        f"{stem}-{SIZE[0]}x{SIZE[1]}.{extension}", ContentFile(output.getvalue()), save=False
    )
    variant.save()


def sharing_image(snapshot):
    """The published sharing image: {"file", "width", "height", "alt"}, or None."""
    image = snapshot.get("images", {}).get("social", {}).get("light")
    if not image:
        return None
    for variant in image.get("variants", []):
        if variant.get("purpose") == "social":
            return {
                "file": variant["file"],
                "width": SIZE[0],
                "height": SIZE[1],
                "alt": image["alt"],
            }
    return None
