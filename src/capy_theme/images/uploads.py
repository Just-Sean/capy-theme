"""Checking and cleaning uploaded images, and storing them as ThemeAssets."""

import io
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError

from .. import conf
from .gif_frames import BrokenGif, frame_disposals, frame_extent
from .slots import MODES, NO_SVG, SLOTS
from .svg import clean_svg

# Image info Pillow may write back when saving that is safe to keep.
KEEP_INFO = ("icc_profile", "transparency", "duration", "loop", "background")
NOT_AN_IMAGE = "That file isn't a supported image (PNG, JPEG, WebP, GIF or SVG)."
# What Pillow raises while decoding or saving a damaged file (e.g. "image file is
# truncated"). Only these become NOT_AN_IMAGE: anything else (running out of
# memory, a bug) stays a server error, which Django logs, so it gets noticed.
DAMAGED_FILE_ERRORS = (OSError, Image.DecompressionBombError)


# Pillow format -> (content type, file extension)
FORMATS = {
    "PNG": ("image/png", "png"),
    "JPEG": ("image/jpeg", "jpg"),
    "WEBP": ("image/webp", "webp"),
    "GIF": ("image/gif", "gif"),
}


def byte_limit(slot):
    """The largest upload for a slot: its own limit, or CAPY_THEME_IMAGE_MAX_BYTES if
    that's lower."""
    cap = conf.get("CAPY_THEME_IMAGE_MAX_BYTES")
    return min(SLOTS[slot][1], cap) if cap else SLOTS[slot][1]


def prepare_image(data, name, slot):
    """Check an uploaded image and return a clean copy.

    Returns {"file": ContentFile, "width", "height", "content_type", "size"}.
    The type is worked out from the content, not the name. Raises
    ValidationError if it's too big, isn't a supported image, or is too large.
    """
    label, _limit, max_pixels, _help = SLOTS[slot]
    max_bytes = byte_limit(slot)
    if len(data) > max_bytes:
        raise ValidationError(
            f"The {label.lower()} is too big ({len(data) // 1024} KB; the limit is "
            f"{max_bytes // 1024} KB)."
        )
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
        raise ValidationError(NOT_AN_IMAGE) from error
    if image.format not in FORMATS:
        raise ValidationError(NOT_AN_IMAGE)
    # Checked before decoding, so a huge image is never unpacked into memory.
    frames, width, height = _frames_and_size(image, data)
    if max(width, height) > max_pixels:  # (not for SVGs: they have no pixels)
        raise ValidationError(
            f"The image is {width} × {height} pixels; the {label.lower()} can be "
            f"at most {max_pixels} pixels wide or high."
        )
    if frames > 1:
        _check_animation(frames, width, height)
    return _clean_copy(image, name, data)


def _frames_and_size(image, data):
    """(frames, width, height), read without decoding. WebP and PNG state their
    frame count, and only their first frame is ever decoded.

    A GIF's frames each have their own position and size, and one can reach past
    the size the image states. Pillow then grows the image while decoding (after
    any check), or fails. Every frame's header is read (images/gif_frames.py), and
    a GIF whose frames don't fit inside it is refused: GIF tools don't make them.
    """
    if image.format != "GIF":
        return getattr(image, "n_frames", 1), image.width, image.height
    try:
        frames, width, height = frame_extent(data)
    except BrokenGif as error:
        raise ValidationError(NOT_AN_IMAGE) from error
    if (width, height) != image.size:
        raise ValidationError(
            f"That GIF is damaged: a frame reaches past its edges ({image.width} × "
            f"{image.height} pixels). Save it again from an image editor."
        )
    return frames, width, height


def _clean_copy(image, name, data):
    """Decode the image and save a copy without metadata (see prepare_image)."""
    try:
        image.load()
    except DAMAGED_FILE_ERRORS as error:
        raise ValidationError(NOT_AN_IMAGE) from error
    content_type, extension = FORMATS[image.format]
    clean = _strip_metadata(image)
    save_options = {"format": image.format}
    if image.format == "JPEG":
        save_options |= {"quality": 92, "optimize": True}
    elif image.format == "PNG":
        save_options |= {"optimize": True}
    elif image.format == "GIF" and getattr(image, "is_animated", False):
        # Saving every frame goes back to the first one, which re-reads its info
        # from the file (comment included), and Pillow writes that into the new
        # file's header. An empty comment means none is written (issue #185).
        # Each frame keeps how it's cleared before the next (e.g. "clear to the
        # background"); otherwise earlier frames would stay visible (issue #189).
        save_options |= {"save_all": True, "comment": b"", "disposal": _disposal(data)}
    try:
        output = _save(clean, save_options)  # decodes every frame of an animation
    except DAMAGED_FILE_ERRORS as error:
        raise ValidationError(NOT_AN_IMAGE) from error
    return {
        "file": ContentFile(output.getvalue(), name=f"{Path(name).stem}.{extension}"),
        "width": clean.width,
        "height": clean.height,
        "content_type": content_type,
        "size": output.tell(),
    }


def _disposal(data):
    """Pillow's disposal option for an animated GIF: one number when every frame
    uses the same (the usual case), otherwise one per frame."""
    disposals = frame_disposals(data)
    return disposals[0] if len(set(disposals)) == 1 else disposals


def _save(clean, save_options):
    """The saved image's bytes (in a BytesIO)."""
    output = io.BytesIO()
    try:
        clean.save(output, **save_options)
    except TypeError:
        # A Pillow bug: when every frame is the same it saves one still frame, and
        # that can't take a list of disposals. Disposal doesn't change a still
        # frame, so save it without.
        if not isinstance(save_options.get("disposal"), list):
            raise
        output = io.BytesIO()
        clean.save(output, **{k: v for k, v in save_options.items() if k != "disposal"})
    return output


def _check_animation(frames, width, height):
    """Refuse animations that are too big, too long, or have too many pixels in all.

    A frame that changes a few pixels takes a few bytes in the file but is decoded
    at full size when the animation is saved again (issue #188). Pillow keeps every
    frame that differs from the one before at full size until it has written them
    all, so memory and time grow with the total pixels (measured: about 2 bytes
    and 20 ns per pixel, plus about 80 MB of working copies at 2000 × 2000: about
    150 MB and 1 s at the defaults). The frame size cap limits the working copies.
    """
    max_size = conf.positive_int("CAPY_THEME_ANIMATION_MAX_SIZE")
    if max(width, height) > max_size:
        raise ValidationError(
            f"The animation is {width} × {height} pixels; animated images can be at most "
            f"{max_size} pixels wide or high. Make it smaller."
        )
    max_frames = conf.positive_int("CAPY_THEME_ANIMATION_MAX_FRAMES")
    if frames > max_frames:
        raise ValidationError(
            f"The animation has {frames} frames; animated images can have at most "
            f"{max_frames}. Make it shorter."
        )
    total = frames * width * height
    max_total = conf.positive_int("CAPY_THEME_ANIMATION_MAX_PIXELS")
    if total > max_total:
        raise ValidationError(
            f"The animation is too big: {frames} frames of {width} × {height} pixels "
            f"({total:,} in all; at most {max_total:,}). Make it shorter or smaller."
        )


def _strip_metadata(image):
    """A copy of the image with no EXIF, text chunks or comments.

    Photos are turned upright first (their EXIF says how they were held), so they
    still look right once the EXIF is gone. Color profiles are kept: they don't
    identify anyone and keep colors accurate.
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
    from .models import ThemeAsset
    from .sharing import make_sharing_image
    from .variants import make_variants

    if slot not in SLOTS:
        raise ValidationError("Choose where the image goes.")
    if mode not in dict(MODES):
        raise ValidationError("Choose light or dark mode.")
    max_bytes = byte_limit(slot)
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
