"""Checking, converting and trimming font files (uploads and imports).

Any WOFF2, WOFF, TTF or OTF file is checked with fontTools (so a renamed image
is refused), converted to WOFF2, and optionally trimmed to one character subset.
"""

import io
import logging
import struct
import zlib
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from fontTools import subset as subsetter
from fontTools.ttLib import TTFont, TTLibError

# Google Fonts' standard character subsets, as CSS unicode-range values.
SUBSETS = {
    "latin": "U+0000-00FF, U+0131, U+0152-0153, U+02BB-02BC, U+02C6, U+02DA, U+02DC, "
    "U+0304, U+0308, U+0329, U+2000-206F, U+20AC, U+2122, U+2191, U+2193, U+2212, "
    "U+2215, U+FEFF, U+FFFD",
    "latin-ext": "U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, "
    "U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, "
    "U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF",
    "cyrillic": "U+0301, U+0400-045F, U+0490-0491, U+04B0-04B1, U+2116",
    "greek": "U+0370-0377, U+037A-037F, U+0384-038A, U+038C, U+038E-03A1, U+03A3-03FF",
    "vietnamese": "U+0102-0103, U+0110-0111, U+0128-0129, U+0168-0169, U+01A0-01A1, "
    "U+01AF-01B0, U+0300-0301, U+0303-0304, U+0308-0309, U+0323, U+0329, U+1EA0-1EF9, "
    "U+20AB",
}
SUBSET_CHOICES = [("all", "All characters (don't trim)")] + [
    (name, name.replace("-", " ").capitalize()) for name in SUBSETS
]
DEFAULT_MAX_BYTES = 5 * 1024 * 1024

# What fontTools raises for files that aren't fonts (or are broken ones).
PARSE_ERRORS = (
    TTLibError,
    AssertionError,
    struct.error,
    zlib.error,
    ValueError,
    KeyError,
    IndexError,
    OSError,
    TypeError,
)


def max_bytes():
    return getattr(settings, "CAPY_THEME_FONT_MAX_BYTES", DEFAULT_MAX_BYTES)


def codepoints(unicode_range):
    """Return the set of code points in a CSS unicode-range value."""
    points = set()
    for part in unicode_range.split(","):
        part = part.strip().removeprefix("U+")
        start, _, end = part.partition("-")
        points.update(range(int(start, 16), int(end or start, 16) + 1))
    return points


def prepare(data, name, subset="all"):
    """Check a font file and return it as WOFF2, with what it says about itself.

    Returns {"file": ContentFile(woff2), "weight", "style", "family",
    "unicode_range"}. Raises ValidationError if it's too big or isn't a font, or
    if trimming leaves no characters.
    """
    if len(data) > max_bytes():
        raise ValidationError(
            f"The font file is too big ({len(data) // 1024} KB; the limit is "
            f"{max_bytes() // 1024} KB)."
        )
    try:
        font = TTFont(io.BytesIO(data))
        font.getGlyphOrder()  # make sure it really parses
    except PARSE_ERRORS as error:
        raise ValidationError("That file isn't a font (WOFF2, WOFF, TTF or OTF).") from error
    unicode_range = ""
    if subset != "all":
        unicode_range = SUBSETS[subset]
        wanted = codepoints(unicode_range) & set(font.getBestCmap() or {})
        if not wanted:
            raise ValidationError(f"The font has no {subset} characters.")
        options = subsetter.Options()
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.notdef_outline = True
        trimmer = subsetter.Subsetter(options=options)
        trimmer.populate(unicodes=wanted)
        # fontTools notes every table it drops (e.g. font-editor data); not useful here.
        quiet = logging.getLogger("fontTools.subset")
        level = quiet.level
        quiet.setLevel(logging.ERROR)
        try:
            trimmer.subset(font)
        finally:
            quiet.setLevel(level)
    os2 = font["OS/2"] if "OS/2" in font else None
    weight = os2.usWeightClass if os2 else 400
    italic = bool(os2 and os2.fsSelection & 1) or ("head" in font and font["head"].macStyle & 2)
    family = _family(font)
    font.flavor = "woff2"
    output = io.BytesIO()
    font.save(output)
    return {
        "file": ContentFile(output.getvalue(), name=f"{Path(name).stem}.woff2"),
        "weight": min(max(int(weight), 100), 900),
        "style": "italic" if italic else "normal",
        "family": family,
        "unicode_range": unicode_range,
    }


def _family(font):
    names = font["name"] if "name" in font else None
    if names is None:
        return ""
    for name_id in (16, 1):  # typographic family, then family
        record = names.getName(name_id, 3, 1, 0x409) or names.getName(name_id, 1, 0, 0)
        if record:
            return record.toUnicode()
    return ""
