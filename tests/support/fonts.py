"""Tiny fonts for tests, built with fontTools (no system fonts needed).

Real ones (`ttf_bytes`), and hostile ones for the #191 limits: compressed files
that unpack to more than they should, and fonts that are costly to read.
"""

import hashlib
import io
import struct
import zlib

import brotli
from fontTools.cffLib import SubrsIndex
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.psCharStrings import T2CharString
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont
from fontTools.ttLib.sfnt import SFNTWriter
from fontTools.ttLib.tables.DefaultTable import DefaultTable

# Latin A, Latin-extended Ā, Cyrillic Ж
CHARACTERS = {"A": 0x41, "Amacron": 0x100, "Zhe": 0x416}
NAME_TABLE = 5  # the index WOFF2 uses for a 'name' table


def square():
    pen = TTGlyphPen(None)
    pen.moveTo((100, 0))
    pen.lineTo((100, 700))
    pen.lineTo((500, 700))
    pen.lineTo((500, 0))
    pen.closePath()
    return pen.glyph()


def ttf_bytes(family="Test Sans", weight=400, italic=False):
    """Return a small valid TTF font with a few characters."""
    builder = FontBuilder(1000, isTTF=True)
    glyphs = [".notdef", *CHARACTERS]
    builder.setupGlyphOrder(glyphs)
    builder.setupCharacterMap({code: name for name, code in CHARACTERS.items()})
    builder.setupGlyf({name: square() for name in glyphs})
    builder.setupHorizontalMetrics({name: (600, 100) for name in glyphs})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable({"familyName": family, "styleName": "Italic" if italic else "Regular"})
    builder.setupOS2(usWeightClass=weight, fsSelection=0x01 if italic else 0x40)
    builder.updateHead(macStyle=0x02 if italic else 0)
    builder.setupPost()
    output = io.BytesIO()
    builder.save(output)
    return output.getvalue()


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


def real_font_with_extra(flavor, extra_bytes, fill=None):
    """A real font saved as WOFF or WOFF2, with an extra table (honest sizes).

    The table is `extra_bytes` zeros, which pack small, or the bytes in `fill`.
    """
    font = TTFont(io.BytesIO(ttf_bytes()))
    extra = DefaultTable("zzzz")
    extra.data = b"\0" * extra_bytes if fill is None else fill[:extra_bytes]
    font["zzzz"] = extra
    font.flavor = flavor
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


def many_points_font(glyphs, flavor=None):
    """A valid TrueType font whose `glyphs` glyphs each have 65,536 points.

    Each glyph takes about 530 bytes (repeated flags), but fontTools builds an
    object per point, so reading it costs about 1.5 MB per glyph.
    """
    names = [".notdef"] + [f"g{n}" for n in range(1, glyphs)]
    builder = FontBuilder(1000, isTTF=True)
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap({0x41 + n: names[n] for n in range(1, min(glyphs, 26))})
    builder.setupGlyf({name: TTGlyphPen(None).glyph() for name in names})
    builder.setupHorizontalMetrics({name: (500, 0) for name in names})
    builder.setupHorizontalHeader()
    builder.setupNameTable({"familyName": "Points", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    plain = io.BytesIO()
    builder.save(plain)
    reader = TTFont(io.BytesIO(plain.getvalue())).reader
    # One contour of 65,536 points: flag 0x39 (on curve, x and y repeat) × 256, 256 times.
    glyph = struct.pack(">hhhhhHH", 1, 0, 0, 0, 0, 65534, 0)
    glyph += bytes([0x39, 255]) * 255 + bytes([0x39, 254])
    glyph += b"\0" * (-len(glyph) % 4)
    offsets = [0, 0] + [len(glyph) * n for n in range(1, glyphs)]
    head = bytearray(reader["head"])
    head[50:52] = struct.pack(">h", 1)  # long loca offsets
    maxp = bytearray(reader["maxp"])
    maxp[6:10] = struct.pack(">HH", 65535, 1)  # max points, max contours
    tables = {tag: reader[tag] for tag in reader.keys()}
    tables.update(
        glyf=glyph * (glyphs - 1),
        loca=b"".join(struct.pack(">L", offset) for offset in offsets),
        head=bytes(head),
        maxp=bytes(maxp),
    )
    out = io.BytesIO()
    writer = SFNTWriter(out, len(tables), flavor=flavor)
    for tag in sorted(tables):
        writer[tag] = tables[tag]
    writer.close()
    return out.getvalue()


def self_calling_cff_font():
    """An OTF (CFF) font whose glyph A calls a subroutine that calls itself forever."""
    names = [".notdef", "A"]
    builder = FontBuilder(1000, isTTF=False)
    builder.setupGlyphOrder(names)
    builder.setupCharacterMap({0x41: "A"})
    charstrings = {}
    for name in names:
        pen = T2CharStringPen(500, None)
        pen.moveTo((0, 0))
        pen.lineTo((100, 100))
        pen.closePath()
        charstrings[name] = pen.getCharString()
    builder.setupCFF("Loop", {"FullName": "Loop"}, charstrings, {})
    builder.setupHorizontalMetrics({name: (500, 0) for name in names})
    builder.setupHorizontalHeader()
    builder.setupNameTable({"familyName": "Loop", "styleName": "Regular"})
    builder.setupOS2()
    builder.setupPost()
    cff = builder.font["CFF "].cff
    private = cff.topDictIndex[0].Private
    subrs = SubrsIndex(private=private, globalSubrs=cff.GlobalSubrs)
    # Subroutine 0 is called as -107 (the bias for fewer than 1240 subroutines).
    subrs.append(T2CharString(program=[-107, "callsubr"], private=private))
    private.Subrs = subrs
    cff.topDictIndex[0].CharStrings["A"].program = [500, -107, "callsubr", "endchar"]
    builder.font.recalcBBoxes = False
    out = io.BytesIO()
    builder.font.save(out)
    return out.getvalue()
