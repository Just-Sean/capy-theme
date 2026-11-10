"""Tiny real fonts for tests, built with fontTools (no system fonts needed)."""

import io

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

# Latin A, Latin-extended Ā, Cyrillic Ж
CHARACTERS = {"A": 0x41, "Amacron": 0x100, "Zhe": 0x416}


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
