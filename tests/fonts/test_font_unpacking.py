"""Fonts that would unpack into huge amounts of data are refused before fontTools (#191).

The hostile files are built here, small: a few MB of zeros compressed into a few
KB, against a limit lowered to 1 MB, so the tests stay fast.
"""

import time
import tracemalloc

import pytest
from django.core.exceptions import ImproperlyConfigured, ValidationError

from capy_theme.fonts.uploads import prepare
from tests.support.fonts import noise, real_font_with_extra, woff, woff2

MB = 1024 * 1024


@pytest.fixture(autouse=True)
def small_limit(settings):
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = MB


@pytest.mark.parametrize("make", [woff2, woff])
def test_a_file_that_says_it_unpacks_past_the_limit_is_refused(make):
    with pytest.raises(ValidationError, match="too big once unpacked"):
        prepare(make(10, 2 * MB), "big.woff2")


@pytest.mark.parametrize("make", [woff2, woff])
def test_a_file_that_unpacks_to_more_than_it_says_is_refused(make):
    with pytest.raises(ValidationError, match="unpacks to more than it says"):
        prepare(make(4 * MB, 100_000), "liar.woff2")


@pytest.mark.parametrize("make", [woff2, woff])
def test_a_file_that_unpacks_to_far_more_than_it_says_is_refused(make):
    """Lying by more than one unpacking step (1 MB) is caught too, not just the first step."""
    with pytest.raises(ValidationError, match="unpacks to more than it says"):
        prepare(make(40 * MB, MB // 2), "liar.woff2")


@pytest.mark.parametrize("make", [woff2, woff])
def test_metadata_that_says_it_unpacks_past_the_limit_is_refused(make):
    with pytest.raises(ValidationError, match="too big once unpacked"):
        prepare(make(10, 10, meta=(10, 2 * MB)), "meta.woff2")


@pytest.mark.parametrize("make", [woff2, woff])
def test_metadata_that_unpacks_to_more_than_it_says_is_refused(make):
    with pytest.raises(ValidationError, match="unpacks to more than it says"):
        prepare(make(10, 10, meta=(4 * MB, 100_000)), "meta.woff2")


@pytest.mark.parametrize("flavor", ["woff", "woff2"])
def test_a_real_font_with_honest_sizes_over_the_limit_is_refused(flavor):
    """The review's case: a valid WOFF with a huge table of zeros was accepted."""
    with pytest.raises(ValidationError, match="too big once unpacked"):
        prepare(real_font_with_extra(flavor, 2 * MB), "f.woff")


@pytest.mark.parametrize("flavor", ["woff", "woff2"])
def test_a_real_font_under_the_limit_is_accepted(flavor):
    result = prepare(real_font_with_extra(flavor, 100_000), "f.woff")
    assert result["file"].read()[:4] == b"wOF2"


def test_a_woff2_font_bigger_than_one_unpacking_step_is_accepted(settings):
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = 4 * MB
    result = prepare(real_font_with_extra("woff2", 3 * MB), "f.woff2")
    assert result["file"].read()[:4] == b"wOF2"


def test_a_woff2_font_collection_is_refused():
    with pytest.raises(ValidationError, match="collections"):
        prepare(woff2(10, 10, flavor=b"ttcf"), "c.woff2")


@pytest.mark.parametrize(
    "data",
    [
        b"wOF2" + b"\0" * 10,  # header cut short
        b"wOFF" + b"\0" * 10,
        woff2(10, 10)[:52] + b"not brotli at all" * 4,  # damaged compressed data
        woff(10, 10)[:64] + b"not zlib at all" * 4,
        # compressed data that stops short: covers the "data ends early" return in
        # unpacking._unpack_brotli (bytes that don't compress, then cut)
        real_font_with_extra("woff2", 50_000, fill=noise(50_000))[:-2000],
    ],
)
def test_a_broken_file_is_not_a_font_rather_than_a_server_error(data):
    with pytest.raises(ValidationError, match="isn't a font"):
        prepare(data, "broken.woff2")


@pytest.mark.parametrize("make", [woff2, woff])
def test_refusing_a_bomb_is_quick_and_uses_little_memory(make, settings):
    """At the real 30 MB default, a file that unpacks to 40 MB is stopped early."""
    del settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES
    bomb = make(40 * MB, 100_000)
    tracemalloc.start()
    started = time.monotonic()
    try:
        with pytest.raises(ValidationError, match="unpacks to more than it says"):
            prepare(bomb, "bomb.woff2")
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert time.monotonic() - started < 2
    assert peak < 5 * MB


@pytest.mark.parametrize("value", [0, None, "30MB"])
def test_the_limit_must_be_a_positive_whole_number(settings, value):
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = value
    with pytest.raises(ImproperlyConfigured):
        prepare(woff2(10, 10), "f.woff2")
