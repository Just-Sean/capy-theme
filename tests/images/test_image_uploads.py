"""Tests for checking and cleaning uploaded images (issue #32)."""

import io
import struct
import zlib

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import ExifTags, Image, PngImagePlugin

from capy_theme.images.models import ThemeAsset
from capy_theme.images.slots import SLOTS
from capy_theme.images.uploads import add_asset, prepare_image
from capy_theme.models import Theme

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


def gps_photo(orientation=None, size=(40, 20)):
    """A JPEG with camera details and a GPS location in its EXIF."""
    image = Image.new("RGB", size, (200, 30, 30))
    exif = image.getexif()
    exif[ExifTags.Base.Make] = "Spy Camera"
    if orientation:
        exif[ExifTags.Base.Orientation] = orientation
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N"
    gps[ExifTags.GPS.GPSLatitude] = (51.0, 30.0, 0.0)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


def png(size=(10, 10), text=None, mode="RGBA"):
    info = PngImagePlugin.PngInfo()
    if text:
        info.add_text("Comment", text)
    buffer = io.BytesIO()
    Image.new(mode, size, (0, 128, 255, 255) if mode == "RGBA" else 0).save(
        buffer, "PNG", pnginfo=info
    )
    return buffer.getvalue()


def reopen(clean):
    return Image.open(io.BytesIO(clean["file"].read()))


def test_the_issue_check_gps_is_removed():
    data = gps_photo()
    original = Image.open(io.BytesIO(data)).getexif()
    assert original.get_ifd(ExifTags.IFD.GPSInfo)  # the test photo really has GPS
    clean = prepare_image(data, "holiday.jpg", "logo_main")
    image = reopen(clean)
    assert image.format == "JPEG"
    assert not image.getexif()  # no EXIF at all: no GPS, no camera
    clean["file"].seek(0)
    stored = clean["file"].read()
    assert b"Spy Camera" not in stored
    assert b"Exif" not in stored
    assert clean["content_type"] == "image/jpeg"
    assert (clean["width"], clean["height"]) == (40, 20)


def test_the_issue_check_renamed_text_file_is_rejected():
    with pytest.raises(ValidationError, match="isn't a supported image"):
        prepare_image(b"just some text, honest\n" * 10, "logo.png", "logo_main")


def test_a_truncated_image_is_rejected():
    with pytest.raises(ValidationError, match="isn't a supported image"):
        prepare_image(png((50, 50))[:60], "logo.png", "logo_main")


def test_an_unsupported_format_is_rejected():
    buffer = io.BytesIO()
    Image.new("RGB", (4, 4)).save(buffer, "BMP")
    with pytest.raises(ValidationError, match="isn't a supported image"):
        prepare_image(buffer.getvalue(), "logo.bmp", "logo_main")


def test_the_type_comes_from_the_content_not_the_name():
    clean = prepare_image(png(), "logo.jpg", "logo_main")
    assert clean["content_type"] == "image/png"
    assert clean["file"].name == "logo.png"


def test_photos_are_turned_upright_before_the_exif_goes():
    # Orientation 6: the camera was turned, so the picture should be shown rotated.
    clean = prepare_image(gps_photo(orientation=6, size=(40, 20)), "p.jpg", "logo_main")
    assert (clean["width"], clean["height"]) == (20, 40)


def test_png_text_chunks_are_removed_and_transparency_kept():
    clean = prepare_image(png(text="secret note"), "logo.png", "logo_main")
    image = reopen(clean)
    assert "Comment" not in image.info
    assert image.mode == "RGBA"


def test_size_limit_per_slot(monkeypatch):
    data = png((10, 10))
    label, _limit, pixels, text = SLOTS["logo_email"]
    monkeypatch.setitem(SLOTS, "logo_email", (label, len(data) - 1, pixels, text))
    with pytest.raises(ValidationError, match="too big"):
        prepare_image(data, "logo.png", "logo_email")
    prepare_image(data, "logo.png", "logo_main")  # other slots have their own limit


def test_pixel_limit_per_slot():
    max_pixels = SLOTS["logo_email"][2]
    with pytest.raises(ValidationError, match="pixels"):
        prepare_image(png((max_pixels + 1, 1), mode="L"), "wide.png", "logo_email")


def test_every_slot_has_a_label_limit_and_help():
    for label, max_bytes, max_pixels, text in SLOTS.values():
        assert label and text and max_bytes > 0 and max_pixels > 0


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


def test_add_asset_stores_a_clean_copy(theme):
    upload = SimpleUploadedFile("holiday.jpg", gps_photo(), content_type="image/jpeg")
    asset = add_asset(theme, "logo_main", "dark", upload, "Our logo")
    asset.refresh_from_db()
    assert (asset.slot, asset.mode, asset.alt_text) == ("logo_main", "dark", "Our logo")
    assert asset.content_type == "image/jpeg"
    assert asset.original.name.startswith("capy_theme/assets/logo_main/")
    with asset.original.open("rb") as f:
        stored = f.read()
    assert asset.size == len(stored)
    assert not Image.open(io.BytesIO(stored)).getexif()


def test_add_asset_rejects_unknown_slots_and_modes(theme):
    upload = SimpleUploadedFile("a.png", png())
    with pytest.raises(ValidationError):
        add_asset(theme, "nowhere", "light", upload)
    with pytest.raises(ValidationError):
        add_asset(theme, "logo_main", "sepia", upload)
    assert not ThemeAsset.objects.exists()


# Corrupt files and GIFs (issue #181).


def test_an_image_that_only_breaks_when_decoded_is_rejected():
    # The chunk checksums are right, so Pillow's quick check passes, but the
    # pixel data is garbage: decoding it fails, and that's "not an image" too.
    data = png(mode="RGB")
    start = data.index(b"IDAT") - 4
    length = struct.unpack(">I", data[start : start + 4])[0]
    garbage = b"\x78\x9c" + b"\xff" * 20
    chunk = (
        struct.pack(">I", len(garbage))
        + b"IDAT"
        + garbage
        + struct.pack(">I", zlib.crc32(b"IDAT" + garbage))
    )
    broken = data[:start] + chunk + data[start + 12 + length :]
    with pytest.raises(ValidationError, match="isn.t a supported image"):
        prepare_image(broken, "logo.png", "logo_main")


def gif(frames=1, comment=b""):
    # Clearly different frames: Pillow merges identical ones into one.
    images = [Image.new("RGB", (10, 10), c) for c in ["red", "green", "blue"][:frames]]
    buffer = io.BytesIO()
    images[0].save(
        buffer, "GIF", save_all=frames > 1, append_images=images[1:], comment=comment, duration=100
    )
    return buffer.getvalue()


def test_gif_comments_are_removed():
    clean = prepare_image(gif(comment=b"made by Spy Camera"), "a.gif", "logo_main")
    assert clean["content_type"] == "image/gif"
    assert "comment" not in reopen(clean).info


def test_animated_gifs_keep_every_frame():
    clean = prepare_image(gif(frames=3), "a.gif", "logo_main")
    image = reopen(clean)
    assert image.is_animated and image.n_frames == 3
