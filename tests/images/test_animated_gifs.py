"""Animated GIF uploads: metadata, timing, transparency and disposal survive the
cleaning (issues #185 and #189). Limits on animations are in test_animation_limits.py."""

import io

import pytest
from PIL import Image

from capy_theme.images.gif_frames import frame_disposals
from capy_theme.images.uploads import prepare_image
from tests.support.images import gif, hand_built_gif, reopen


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


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


def moving_square_gif(disposal):
    """Three frames of a square moving across a transparent background, saved with
    the given disposal (how each frame is cleared before the next)."""
    frames = []
    for step, color in enumerate([(255, 0, 0, 255), (0, 128, 0, 255), (0, 0, 255, 255)]):
        frame = Image.new("RGBA", (12, 12), (0, 0, 0, 0))
        frame.paste(Image.new("RGBA", (4, 4), color), (step * 4, step * 4))
        frames.append(frame)
    buffer = io.BytesIO()
    frames[0].save(
        buffer, "GIF", save_all=True, append_images=frames[1:], duration=100, disposal=disposal
    )
    return buffer.getvalue()


def every_frame_rgba(data):
    return every_frame(
        Image.open(io.BytesIO(data)), lambda frame: list(frame.convert("RGBA").get_flattened_data())
    )


@pytest.mark.parametrize("disposal", [0, 1, 2])
def test_animated_gifs_look_the_same_after_cleaning(disposal):
    # Issue #189: with disposal 2 ("clear to the background") the cleaned copy
    # lost it, so earlier frames' squares stayed visible in later frames.
    data = moving_square_gif(disposal)
    clean = prepare_image(data, "a.gif", "logo_main")["file"].read()
    assert every_frame_rgba(clean) == every_frame_rgba(data)


def test_frame_disposals_are_read_from_the_file():
    assert frame_disposals(moving_square_gif(2)) == [2, 2, 2]
    assert frame_disposals(moving_square_gif([1, 2, 1])) == [1, 2, 1]
    assert frame_disposals(hand_built_gif(10, [(1, 1), (1, 1)])) == [0, 0]  # not set


def test_identical_frames_with_different_disposals_dont_crash():
    # Pillow saves identical frames as one still frame, which can't take a list of
    # disposals (a Pillow bug); the still frame is saved without it.
    data = hand_built_gif(10, [(1, 1), (1, 1)])
    second_gce = data.index(b"\x21\xf9\x04", data.index(b"\x21\xf9\x04") + 1)
    data = data[: second_gce + 3] + bytes([2 << 2]) + data[second_gce + 4 :]  # frame 2: disposal 2
    assert frame_disposals(data) == [0, 2]
    clean = prepare_image(data, "a.gif", "logo_main")
    assert clean["content_type"] == "image/gif"
