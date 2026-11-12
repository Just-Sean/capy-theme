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


def gif(frames=1, comment=b"", duration=100, loop=None, transparent=False):
    """A GIF; frames are clearly different (Pillow merges identical ones)."""
    colors = ["red", "green", "blue"][:frames]
    if transparent:  # a colored square on a transparent background
        images = []
        for color in colors:
            frame = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
            frame.paste(Image.new("RGBA", (5, 5), color), (0, 0))
            images.append(frame)
    else:
        images = [Image.new("RGB", (10, 10), color) for color in colors]
    extra = {} if loop is None else {"loop": loop}
    buffer = io.BytesIO()
    images[0].save(
        buffer,
        "GIF",
        save_all=frames > 1,
        append_images=images[1:],
        comment=comment,
        duration=duration,
        **extra,
    )
    return buffer.getvalue()


def every_frame(image, read):
    """read(image) for each frame of an (animated) image."""
    values = []
    for index in range(getattr(image, "n_frames", 1)):
        image.seek(index)
        values.append(read(image))
    return values


def gif_extensions(data):
    """(label, application id) of every extension block in a GIF, found by walking
    the file's structure. 0xFE is a comment, 0xFF an application block (e.g.
    NETSCAPE2.0 for looping, XMP), 0xF9 a frame's timing and transparency."""
    flags = data[10]
    pos = 13 + (3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0)
    found = []

    def after_sub_blocks(pos):
        while data[pos]:
            pos += data[pos] + 1
        return pos + 1

    while data[pos] != 0x3B:  # the trailer
        if data[pos] == 0x21:  # an extension
            label = data[pos + 1]
            found.append((label, data[pos + 3 : pos + 3 + data[pos + 2]] if label == 0xFF else b""))
            pos = after_sub_blocks(pos + 2)
        else:  # an image: descriptor, optional local color table, LZW data
            local = data[pos + 9]
            pos += 10 + (3 * 2 ** ((local & 7) + 1) if local & 0x80 else 0)
            pos = after_sub_blocks(pos + 1)
    return found


def with_xmp(data, payload=b"<x:xmpmeta>GPS 51.5 -0.1</x:xmpmeta>"):
    """The GIF with an XMP application block added before its first frame."""
    flags = data[10]
    start = 13 + (3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0)
    chunks = b"".join(
        bytes([len(payload[i : i + 255])]) + payload[i : i + 255]
        for i in range(0, len(payload), 255)
    )
    block = b"\x21\xff\x0bXMP DataXMP" + chunks + b"\x00"
    return data[:start] + block + data[start:]


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
    with pytest.raises(ValidationError, match="isn't a supported image"):
        prepare_image(broken, "logo.png", "logo_main")


def test_gif_comments_are_removed():
    data = gif(comment=b"made by Spy Camera")
    assert Image.open(io.BytesIO(data)).info["comment"]  # the test GIF really has one
    clean = prepare_image(data, "a.gif", "logo_main")
    assert clean["content_type"] == "image/gif"
    assert "comment" not in reopen(clean).info


def test_animated_gifs_keep_every_frame():
    clean = prepare_image(gif(frames=3), "a.gif", "logo_main")
    image = reopen(clean)
    assert image.is_animated and image.n_frames == 3


def test_animated_gif_comments_are_removed_from_every_frame():
    # Issue #185: animated GIFs kept their comment.
    data = gif(frames=3, comment=b"made by Spy Camera")

    def comment(image):
        return image.info.get("comment")

    assert all(every_frame(Image.open(io.BytesIO(data)), comment))  # the input has it
    image = reopen(prepare_image(data, "a.gif", "logo_main"))
    assert every_frame(image, comment) == [None, None, None]


def test_animated_gifs_keep_only_the_looping_and_frame_blocks():
    # Checks the file itself, so metadata a future Pillow might write back (XMP,
    # comments) is caught even if Pillow wouldn't read it back.
    data = with_xmp(gif(frames=3, comment=b"made by Spy Camera", loop=0))
    assert (0xFF, b"XMP DataXMP") in gif_extensions(data)  # the input has XMP
    assert (0xFE, b"") in gif_extensions(data)  # and a comment
    clean = prepare_image(data, "a.gif", "logo_main")["file"].read()
    blocks = gif_extensions(clean)
    assert (0xFE, b"") not in blocks
    assert [app for label, app in blocks if label == 0xFF] == [b"NETSCAPE2.0"]
    assert b"GPS" not in clean


def test_animated_gifs_keep_their_timing_and_looping():
    data = gif(frames=3, duration=[100, 200, 300], loop=0)
    image = reopen(prepare_image(data, "a.gif", "logo_main"))
    assert every_frame(image, lambda frame: frame.info["duration"]) == [100, 200, 300]
    assert image.info["loop"] == 0


def test_animated_gifs_keep_their_transparency():
    image = reopen(prepare_image(gif(frames=2, transparent=True), "a.gif", "logo_main"))
    corners = every_frame(image, lambda frame: frame.convert("RGBA").getpixel((8, 8)))
    squares = every_frame(image, lambda frame: frame.convert("RGBA").getpixel((1, 1)))
    assert [alpha for *_, alpha in corners] == [0, 0]  # still see-through
    assert squares == [(255, 0, 0, 255), (0, 128, 0, 255)]


# Limits on animations (issue #188).


def tiny_frames_gif(frames, size=4000):
    """A hand-built GIF: a size × size canvas with `frames` frames, each changing
    one pixel. Each frame is a few bytes in the file but decoded at full size."""
    header = b"GIF89a" + struct.pack("<HHBBB", size, size, 0x80, 0, 0) + b"\0\0\0\xff\xff\xff"
    frame = (
        b"\x21\xf9\x04\x00\x05\x00\x00\x00"  # timing: 50 ms
        + b"\x2c"
        + struct.pack("<HHHHB", 0, 0, 1, 1, 0)  # a 1 × 1 image at the top left
        + b"\x02\x02\x44\x01\x00"  # its pixel data
    )
    return header + frame * frames + b"\x3b"


def test_the_issue_check_a_small_file_with_many_frames_is_refused():
    data = tiny_frames_gif(5000)
    assert len(data) < 200_000  # well under every slot's size limit
    with pytest.raises(ValidationError, match="has 5000 frames"):
        prepare_image(data, "a.gif", "background_login")


def test_a_short_but_huge_animation_is_refused():
    # 40 frames of 4000 × 4000 is 640 million pixels: over the 100 million default.
    with pytest.raises(ValidationError, match="too big: 40 frames of 4000 × 4000"):
        prepare_image(tiny_frames_gif(40), "a.gif", "background_login")


def test_normal_animations_and_still_images_are_accepted():
    assert prepare_image(gif(frames=3), "a.gif", "logo_main")
    assert prepare_image(png(size=(4000, 4000)), "big.png", "background_login")


def test_a_gif_with_a_broken_later_frame_is_rejected_not_a_crash():
    # Its second frame's color table is cut off. Pillow's quick check passes it,
    # then counting the frames raised IndexError (a server error) before this check.
    data = tiny_frames_gif(1, size=10)[:-1] + (
        b"\x21\xf9\x04\x00\x05\x00\x00\x00\x2c"
        + struct.pack("<HHHHB", 0, 0, 1, 1, 0x80)  # says a local color table follows
        + b"\x02"
    )
    with pytest.raises(ValidationError, match="isn't a supported image"):
        prepare_image(data, "a.gif", "logo_main")
