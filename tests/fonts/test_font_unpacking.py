"""Fonts that would unpack into huge amounts of data are refused before fontTools (#191).

The hostile files are built here, small: a few MB of zeros compressed into a few
KB, against a limit lowered to 1 MB, so the tests stay fast.
"""

import hashlib
import io
import struct
import time
import tracemalloc
import zlib

import brotli
import pytest
from django.core.exceptions import ImproperlyConfigured, ValidationError
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables.DefaultTable import DefaultTable

from capy_theme.fonts.uploads import prepare
from tests.support.fonts import ttf_bytes

MB = 1024 * 1024
NAME_TABLE = 5  # the index WOFF2 uses for a 'name' table


@pytest.fixture(autouse=True)
def small_limit(settings):
    settings.CAPY_THEME_FONT_MAX_UNPACKED_BYTES = MB


def base128(number):
    """WOFF2's variable-length number format."""
    parts = []
    while True:
        parts.insert(0, number & 0x7F)
        number >>= 7
        if not number:
            break
    return bytes([part | 0x80 for part in parts[:-1]] + [parts[-1]])


def woff2(zeros, declared, flavor=b"\x00\x01\x00\x00", meta=None):
    """A WOFF2 file with one table that unpacks to `zeros` bytes but says `declared`.

    `meta` is (unpacks to, says) for an optional metadata block.
    """
    packed = brotli.compress(b"\0" * zeros, quality=5)
    entry = bytes([NAME_TABLE]) + base128(declared)
    start = 48 + len(entry)
    meta_packed, meta_says = b"", 0
    if meta:
        meta_packed, meta_says = brotli.compress(b"\0" * meta[0], quality=5), meta[1]
    meta_offset = start + len(packed) if meta else 0
    total = start + len(packed) + len(meta_packed)
    header = struct.pack(
        ">4s4sLHHLLHHLLLLL",
        *(b"wOF2", flavor, total, 1, 0, 12 + 16 + declared, len(packed), 1, 0),
        *(meta_offset, len(meta_packed), meta_says, 0, 0),
    )
    return header + entry + packed + meta_packed


def woff(zeros, declared, meta=None):
    """A WOFF 1.0 file with one zlib table of `zeros` bytes that says `declared`."""
    packed = zlib.compress(b"\0" * zeros, 9)
    start = 44 + 20
    meta_packed, meta_says = b"", 0
    if meta:
        meta_packed, meta_says = zlib.compress(b"\0" * meta[0], 9), meta[1]
    meta_offset = start + len(packed) if meta else 0
    total = start + len(packed) + len(meta_packed)
    header = struct.pack(
        ">4sLLHHLHHLLLLL",
        *(b"wOFF", 0x00010000, total, 1, 0, 12 + 16 + declared, 1, 0),
        *(meta_offset, len(meta_packed), meta_says, 0, 0),
    )
    table = struct.pack(">4sLLLL", b"name", start, len(packed), declared, 0)
    return header + table + packed + meta_packed


def noise(size):
    """Bytes that don't compress (hashes of 0, 1, 2...), the same every run."""
    hashes = (hashlib.sha256(str(n).encode()).digest() for n in range(size // 32 + 1))
    return b"".join(hashes)[:size]


def real_font_with_extra(flavor, extra_bytes, fill=b"\0"):
    """A real font saved as WOFF or WOFF2, with an extra table (honest sizes).

    The table is zeros, which pack small, unless `fill` gives other bytes.
    """
    font = TTFont(io.BytesIO(ttf_bytes()))
    extra = DefaultTable("zzzz")
    extra.data = (fill * extra_bytes)[:extra_bytes]
    font["zzzz"] = extra
    font.flavor = flavor
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


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
        # compressed data that stops short (bytes that don't compress, then cut)
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
