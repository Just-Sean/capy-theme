"""Checking, converting and trimming font files (uploads and imports).

Any WOFF2, WOFF, TTF or OTF file is checked with fontTools (so a renamed image
is refused), converted to WOFF2, and optionally trimmed to one character subset.
"""

import io
import json
import logging
import struct
import zlib
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from fontTools import subset as subsetter
from fontTools.ttLib import TTFont, TTLibError

from .. import conf

# Character sets fonts can be trimmed to, from subsets.json: {name: Unicode ranges}.
SUBSETS = json.loads(Path(__file__).with_name("subsets.json").read_text(encoding="utf-8"))[
    "subsets"
]
SUBSET_CHOICES = [("all", "All characters (don't trim)")] + [
    (name, name.replace("-", " ").capitalize()) for name in SUBSETS
]

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
    return conf.get("CAPY_THEME_FONT_MAX_BYTES")


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
