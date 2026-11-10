"""Theme images: the slots they go in, and checking and cleaning uploads.

Every upload is checked by its content (not its name), limited per slot, and
re-encoded without EXIF and other metadata (camera details, GPS location).
SVGs are cleaned instead (svg.py): scripts, event handlers and links removed.
"""

import io
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .svg import clean_svg

MB = 1024 * 1024

# slot: (label, max bytes, max width or height in pixels, help)
SLOTS = {
    "logo_main": ("Main logo", 2 * MB, 4000, "The logo in the site header."),
    "logo_stacked": ("Stacked logo", 2 * MB, 4000, "Mark above the name, for narrow spaces."),
    "logo_mark": ("Logo mark", 2 * MB, 4000, "The symbol on its own."),
    "logo_wordmark": ("Wordmark", 2 * MB, 4000, "The name on its own."),
    "logo_email": ("Email logo", 1 * MB, 2000, "For HTML emails (PNG is safest)."),
    "logo_print": ("Print logo", 5 * MB, 6000, "High resolution, for print."),
    "icon": ("Icon", 2 * MB, 4000, "One square image: favicons and app icons are made from it."),
    "social": (
        "Social sharing image",
        5 * MB,
        6000,
        "Shown in link previews (cropped to 1200 × 630).",
    ),
    "background_login": ("Login background", 5 * MB, 6000, "Behind the login page."),
    "background_pattern": (
        "Page background pattern",
        2 * MB,
        4000,
        "A tiling pattern behind pages.",
    ),
}
# Slots where SVG can't be used, so a PNG, JPEG, WebP or GIF must be uploaded:
# email clients (Gmail, Outlook) don't show SVG, social sites don't accept it for
# link previews, and favicons and app icons are made from the icon with Pillow.
NO_SVG = {
    "logo_email": "Email programs don't show SVG",
    "social": "Social sites don't accept SVG for link previews",
    "icon": "Favicons and app icons are made from it as PNGs",
}
SLOT_CHOICES = [(slot, spec[0]) for slot, spec in SLOTS.items()]
MODES = [("light", "Light"), ("dark", "Dark")]

# Image info Pillow may write back when saving that is safe to keep.
KEEP_INFO = ("icc_profile", "transparency", "duration", "loop", "background")

# Pillow format -> (content type, file extension)
FORMATS = {
    "PNG": ("image/png", "png"),
    "JPEG": ("image/jpeg", "jpg"),
    "WEBP": ("image/webp", "webp"),
    "GIF": ("image/gif", "gif"),
}


def prepare_image(data, name, slot):
    """Check an uploaded image and return a clean copy.

    Returns {"file": ContentFile, "width", "height", "content_type", "size"}.
    The type is worked out from the content, not the name. Raises
    ValidationError if it's too big, isn't a supported image, or is too large.
    """
    label, max_bytes, max_pixels, _help = SLOTS[slot]
    if len(data) > max_bytes:
        raise ValidationError(
            f"The {label.lower()} is too big ({len(data) // 1024} KB; the limit is "
            f"{max_bytes // 1024} KB)."
        )
    not_an_image = "That file isn't a supported image (PNG, JPEG, WebP, GIF or SVG)."
    if data.lstrip(b"\xef\xbb\xbf \t\r\n").startswith(b"<"):
        # Text starting with "<": only an SVG can be that. Cleaned, not re-encoded.
        if slot in NO_SVG:
            raise ValidationError(
                f"{NO_SVG[slot]}, so the {label.lower()} can't be an SVG. "
                "Upload a PNG or JPEG instead."
            )
        svg, width, height = clean_svg(data)
        return {
            "file": ContentFile(svg, name=f"{Path(name).stem}.svg"),
            "width": width,
            "height": height,
            "content_type": "image/svg+xml",
            "size": len(svg),
        }
    try:
        with Image.open(io.BytesIO(data)) as probe:
            probe.verify()  # catches truncated and corrupt files
        image = Image.open(io.BytesIO(data))
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        SyntaxError,
        ValueError,
    ) as error:
        raise ValidationError(not_an_image) from error
    if image.format not in FORMATS:
        raise ValidationError(not_an_image)
    # Checked before decoding, so a huge image is never unpacked into memory.
    if max(image.size) > max_pixels:  # (not for SVGs: they have no pixels)
        raise ValidationError(
            f"The image is {image.width} × {image.height} pixels; the {label.lower()} can be "
            f"at most {max_pixels} pixels wide or high."
        )
    try:
        image.load()
    except OSError as error:
        raise ValidationError(not_an_image) from error
    content_type, extension = FORMATS[image.format]
    clean = _strip_metadata(image)
    output = io.BytesIO()
    save_options = {"format": image.format}
    if image.format == "JPEG":
        save_options |= {"quality": 92, "optimize": True}
    elif image.format == "PNG":
        save_options |= {"optimize": True}
    elif image.format == "GIF" and getattr(image, "is_animated", False):
        save_options |= {"save_all": True}
    clean.save(output, **save_options)
    return {
        "file": ContentFile(output.getvalue(), name=f"{Path(name).stem}.{extension}"),
        "width": clean.width,
        "height": clean.height,
        "content_type": content_type,
        "size": output.tell(),
    }


def _strip_metadata(image):
    """A copy of the image with no EXIF, text chunks or comments.

    Photos are turned upright first (their EXIF says how they were held), so they
    still look right once the EXIF is gone. Colour profiles are kept: they don't
    identify anyone and keep colours accurate.
    """
    if image.format == "GIF":
        clean = image  # GIFs carry no EXIF; Pillow only writes the comment back
    else:
        clean = ImageOps.exif_transpose(image)
        clean = clean.copy() if clean is image else clean
    clean.info = {key: image.info[key] for key in KEEP_INFO if key in image.info}
    return clean


def add_asset(theme, slot, mode, upload, alt_text=""):
    """Check and clean an uploaded file and store it as a new ThemeAsset.

    `upload` is a Django UploadedFile. Raises ValidationError if the slot, mode
    or file isn't acceptable. Existing assets are never changed.
    """
    from .logos import make_variants
    from .models import ThemeAsset
    from .social import make_sharing_image

    if slot not in SLOTS:
        raise ValidationError("Choose where the image goes.")
    if mode not in dict(MODES):
        raise ValidationError("Choose light or dark mode.")
    max_bytes = SLOTS[slot][1]
    if upload.size is not None and upload.size > max_bytes:
        raise ValidationError(
            f"The {SLOTS[slot][0].lower()} is too big ({upload.size // 1024} KB; the limit is "
            f"{max_bytes // 1024} KB)."
        )
    clean = prepare_image(upload.read(), upload.name, slot)
    asset = ThemeAsset(
        theme=theme,
        slot=slot,
        mode=mode,
        alt_text=alt_text[:200],
        width=clean["width"],
        height=clean["height"],
        size=clean["size"],
        content_type=clean["content_type"],
    )
    asset.original.save(clean["file"].name, clean["file"], save=False)
    asset.save()
    make_variants(asset)
    if slot == "social":
        make_sharing_image(asset)
    return asset


def asset_data(asset):
    """An asset as JSON-ready data (for the editor)."""
    return {
        "id": asset.pk,
        "slot": asset.slot,
        "slot_label": SLOTS.get(asset.slot, (asset.slot,))[0],
        "mode": asset.mode,
        "url": asset.original.url,
        "alt_text": asset.alt_text,
        "width": asset.width,
        "height": asset.height,
        "size": asset.size,
        "content_type": asset.content_type,
    }
