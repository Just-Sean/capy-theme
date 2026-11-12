"""Limits on animated images, so one upload can't use huge amounts of memory or
time (issue #188). The project settings that change them are tested in
tests/test_project_settings.py."""

import io
import struct

import pytest
from django.core.exceptions import ValidationError
from PIL import Image

from capy_theme.images.gif_frames import BrokenGif, frame_extent
from capy_theme.images.uploads import prepare_image
from tests.support.images import gif, hand_built_gif, many_frames_gif

NOT_AN_IMAGE = "isn't a supported image"


def test_the_issue_check_a_small_file_with_many_frames_is_refused():
    data = many_frames_gif(5000, size=100)
    assert len(data) < 200_000  # well under every slot's size limit
    with pytest.raises(ValidationError, match="has 5000 frames"):
        prepare_image(data, "a.gif", "background_login")


def test_too_many_pixels_in_all_is_refused():
    # 30 frames of 2000 × 2000 is 120 million pixels: over the 100 million default.
    with pytest.raises(ValidationError, match="too big: 30 frames of 2000 × 2000"):
        prepare_image(many_frames_gif(30, size=2000), "a.gif", "background_login")


def test_animated_frames_bigger_than_the_animation_limit_are_refused():
    # 2001 px is within the login background's 4000 px, but not for an animation.
    with pytest.raises(ValidationError, match="animated images can be at most 2000 pixels"):
        prepare_image(many_frames_gif(2, size=2001), "a.gif", "background_login")


@pytest.mark.parametrize(
    "frames",
    [
        [(1, 1), (3000, 3000)],  # a later frame bigger than the image says it is
        [(1, 1), (1000, 1000, 2500, 0)],  # a later frame placed past its edge
    ],
)
def test_later_frames_cant_make_the_animation_bigger_than_checked(frames):
    # The image says it's 10 × 10; Pillow would grow it while decoding the frames,
    # after the checks. The frames' own headers are read first, so it's refused.
    data = hand_built_gif(10, frames)
    assert Image.open(io.BytesIO(data)).size == (10, 10)
    with pytest.raises(ValidationError, match="3500 × 1000|3000 × 3000"):
        prepare_image(data, "a.gif", "background_login")


def test_a_one_frame_gif_cant_get_past_the_slots_size_either():
    data = hand_built_gif(10, [(5000, 5000)])
    with pytest.raises(ValidationError, match="5000 × 5000 pixels; the main logo can be at most"):
        prepare_image(data, "a.gif", "logo_main")


def test_normal_animations_and_still_images_are_accepted():
    assert prepare_image(gif(frames=3), "a.gif", "logo_main")
    assert prepare_image(many_frames_gif(3, size=500), "a.gif", "logo_main")


def test_still_images_arent_limited_by_the_animation_settings(settings):
    settings.CAPY_THEME_ANIMATION_MAX_SIZE = 1
    settings.CAPY_THEME_ANIMATION_MAX_PIXELS = 1
    assert prepare_image(gif(frames=1), "a.gif", "logo_main")


# Damaged GIFs are refused as "not a supported image", never a server error.


def test_a_later_frame_with_a_cut_off_color_table():
    # Pillow's quick check passes it, then counting its frames raised IndexError.
    data = hand_built_gif(10, [(1, 1)], trailer=False)
    data += b"\x21\xf9\x04\x00\x05\x00\x00\x00\x2c" + struct.pack("<HHHHB", 0, 0, 1, 1, 0x80)
    with pytest.raises(ValidationError, match=NOT_AN_IMAGE):
        prepare_image(data + b"\x02", "a.gif", "logo_main")


def test_a_later_frame_with_a_cut_off_header():
    data = hand_built_gif(10, [(1, 1)], trailer=False) + b"\x2c\x00\x00\x00"
    with pytest.raises(ValidationError, match=NOT_AN_IMAGE):
        prepare_image(data, "a.gif", "logo_main")


def test_a_later_frame_with_too_little_data():
    # Its header is fine, but its pixel data stops early: only found while saving.
    data = hand_built_gif(10, [(1, 1), (10, 10)])
    with pytest.raises(ValidationError, match=NOT_AN_IMAGE):
        prepare_image(data, "a.gif", "logo_main")


# Reading the frame headers (images/gif_frames.py).


def test_frame_extent_reads_every_frame():
    assert frame_extent(hand_built_gif(10, [(1, 1), (20, 5), (4, 4, 30, 2)])) == (3, 34, 10)


def test_frame_extent_accepts_a_missing_trailer_but_not_a_cut_block():
    assert frame_extent(hand_built_gif(10, [(1, 1)], trailer=False)) == (1, 10, 10)
    with pytest.raises(BrokenGif):
        frame_extent(hand_built_gif(10, [(1, 1)])[:-3])


def test_frame_extent_refuses_junk_where_a_block_should_start():
    data = hand_built_gif(10, [(1, 1)], trailer=False) + b"\x99junk"
    with pytest.raises(BrokenGif, match="Unexpected byte 0x99"):
        frame_extent(data)
    with pytest.raises(ValidationError, match=NOT_AN_IMAGE):
        prepare_image(data, "a.gif", "logo_main")
