"""Refusing font files that would unpack into far more data than any real font (#191).

WOFF and WOFF2 files are compressed, and fontTools unpacks them with no limit, so
a file of a few KB could make the server use gigabytes of memory. `check()` runs
before fontTools sees the file and does two things:

1. Adds up the sizes the file says it unpacks to, and refuses it if that's over
   CAPY_THEME_FONT_MAX_UNPACKED_BYTES.
2. Unpacks each compressed part a little at a time, stopping as soon as it gives
   more than it said. So a file that lies about its sizes is refused before it can
   use more memory than the limit.

TTF and OTF files aren't compressed, so this has nothing to check for them. It
only limits unpacking: a font can still be costly for fontTools to read, so that
runs in its own process with memory and time limits (see `converting`).
"""

import io
import struct
import zlib

from django.core.exceptions import ValidationError
from fontTools.misc import sstruct
from fontTools.ttLib.woff2 import (
    WOFF2DirectoryEntry,
    woff2DirectoryFormat,
    woff2DirectorySize,
)

from .. import conf

try:  # the same choice fontTools makes: brotli on CPython, brotlicffi on PyPy
    import brotli
except ImportError:
    import brotlicffi as brotli

WOFF = b"wOFF"
WOFF2 = b"wOF2"
COLLECTION = "ttcf"  # several fonts in one file (fontTools reads the tag as text)
BROTLI_STEP = 1024 * 1024  # how much brotli unpacks per step (it may give up to ~2x)
WOFF_HEADER = struct.Struct(">4s4sLHHLHHLLLLL")
WOFF_TABLE = struct.Struct(">4sLLLL")  # tag, offset, compressed, unpacked, checksum


def max_unpacked_bytes():
    return conf.positive_int("CAPY_THEME_FONT_MAX_UNPACKED_BYTES")


def check(data):
    """Raise ValidationError if a WOFF or WOFF2 file would unpack past the limit.

    Any other file passes through for fontTools to judge. A file too short or
    broken to read raises the same errors fontTools would (struct.error and so on).
    """
    if data[:4] == WOFF2:
        _check_woff2(data)
    elif data[:4] == WOFF:
        _check_woff(data)


def _check_woff2(data):
    stream = io.BytesIO(data)
    header = sstruct.unpack(woff2DirectoryFormat, stream.read(woff2DirectorySize))
    if header["sfntVersion"] == COLLECTION:
        raise ValidationError("Font collections (several fonts in one file) aren't supported.")
    tables = []
    for _ in range(header["numTables"]):
        entry = WOFF2DirectoryEntry()
        entry.fromFile(stream)
        tables.append(entry)
    packed_tables = sum(entry.length for entry in tables)  # as stored, before rebuilding
    tables_size = max(header["totalSfntSize"], sum(e.origLength for e in tables), packed_tables)
    _refuse_over_limit(tables_size + (header["metaOrigLength"] if header["metaLength"] else 0))

    start = stream.tell()
    _unpack_brotli(data[start : start + header["totalCompressedSize"]], packed_tables)
    if header["metaLength"]:
        offset = header["metaOffset"]
        _unpack_brotli(data[offset : offset + header["metaLength"]], header["metaOrigLength"])


def _check_woff(data):
    header = WOFF_HEADER.unpack_from(data)
    num_tables, total_sfnt_size = header[3], header[5]
    meta_offset, meta_length, meta_unpacked = header[8:11]
    tables = [
        WOFF_TABLE.unpack_from(data, WOFF_HEADER.size + n * WOFF_TABLE.size)
        for n in range(num_tables)
    ]
    tables_size = max(total_sfnt_size, sum(table[3] for table in tables))
    _refuse_over_limit(tables_size + (meta_unpacked if meta_length else 0))

    for _tag, offset, packed, unpacked, _checksum in tables:
        if packed != unpacked:  # stored as-is only when equal; check every other table
            _unpack_zlib(data[offset : offset + packed], unpacked)
    if meta_length:
        _unpack_zlib(data[meta_offset : meta_offset + meta_length], meta_unpacked)


def _refuse_over_limit(size):
    limit = max_unpacked_bytes()
    if size > limit:
        raise ValidationError(
            f"The font is too big once unpacked ({size // 1024} KB; the limit is "
            f"{limit // 1024} KB)."
        )


def _lied():
    return ValidationError("The font file is damaged: it unpacks to more than it says.")


def _unpack_brotli(packed, expected):
    """Unpack in steps, counting, and stop as soon as it passes `expected` bytes."""
    decompressor = brotli.Decompressor()
    produced = 0
    chunk = packed
    while not decompressor.is_finished():
        output = decompressor.process(chunk, output_buffer_limit=BROTLI_STEP)
        chunk = b""  # it already has all the input; later calls only collect output
        produced += len(output)
        if produced > expected:
            raise _lied()
        if not output and decompressor.can_accept_more_data():
            return  # the data ends early: fontTools reports that as "isn't a font"


def _unpack_zlib(packed, expected):
    """Unpack at most one byte more than `expected`, which is enough to catch a lie."""
    if len(zlib.decompressobj().decompress(packed, expected + 1)) > expected:
        raise _lied()
