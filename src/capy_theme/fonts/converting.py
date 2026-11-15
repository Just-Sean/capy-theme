"""Reading, trimming and converting a font with fontTools, in a separate process (#191).

A small font can still make fontTools use gigabytes of memory or minutes of time
(e.g. glyphs packed with hundreds of thousands of points), so `uploads.prepare()`
runs `work()` in its own process, which caps its own memory and CPU time first.
This module doesn't use Django, so that process starts quickly.
"""

import io
import json
import logging
import struct
import zlib
from pathlib import Path

from fontTools import subset as subsetter
from fontTools.ttLib import TTFont, TTLibError

try:
    import resource  # Linux and macOS; Windows has no process limits
except ImportError:
    resource = None

# Character sets fonts can be trimmed to, from subsets.json: {name: Unicode ranges}.
SUBSETS = json.loads(Path(__file__).with_name("subsets.json").read_text(encoding="utf-8"))[
    "subsets"
]

# What fontTools raises for files that aren't fonts (or are broken ones). It reads
# tables only when they're needed, so these can come from any step, not just opening.
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
    UnicodeError,
    RecursionError,
)
try:
    import brotli
except ImportError:
    import brotlicffi as brotli
PARSE_ERRORS += (brotli.error,)


class Refused(Exception):
    """The file is a font, but it can't be used (e.g. it has none of the characters)."""


def codepoints(unicode_range):
    """Return the set of code points in a CSS unicode-range value."""
    points = set()
    for part in unicode_range.split(","):
        part = part.strip().removeprefix("U+")
        start, _, end = part.partition("-")
        points.update(range(int(start, 16), int(end or start, 16) + 1))
    return points


def convert(data, subset="all"):
    """Read a font, trim it to `subset` and return it as WOFF2 with its details.

    Returns {"woff2": bytes, "weight", "style", "family", "unicode_range"}. Raises
    Refused, or one of PARSE_ERRORS if it isn't a font.
    """
    font = TTFont(io.BytesIO(data))
    font.getGlyphOrder()  # make sure it really parses
    unicode_range = ""
    if subset != "all":
        unicode_range = SUBSETS[subset]
        _trim(font, subset, unicode_range)
    os2 = font["OS/2"] if "OS/2" in font else None
    weight = os2.usWeightClass if os2 else 400
    italic = bool(os2 and os2.fsSelection & 1) or ("head" in font and font["head"].macStyle & 2)
    family = _family(font)
    font.flavor = "woff2"
    output = io.BytesIO()
    font.save(output)
    return {
        "woff2": output.getvalue(),
        "weight": min(max(int(weight), 100), 900),
        "style": "italic" if italic else "normal",
        "family": family,
        "unicode_range": unicode_range,
    }


def _trim(font, subset, unicode_range):
    wanted = codepoints(unicode_range) & set(font.getBestCmap() or {})
    if not wanted:
        raise Refused(f"The font has no {subset} characters.")
    options = subsetter.Options()
    options.layout_features = ["*"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    trimmer = subsetter.Subsetter(options=options)
    trimmer.populate(unicodes=wanted)
    # fontTools notes every table it drops (e.g. font-editor data); not useful here.
    logging.getLogger("fontTools.subset").setLevel(logging.ERROR)
    trimmer.subset(font)


def _family(font):
    names = font["name"] if "name" in font else None
    if names is None:
        return ""
    for name_id in (16, 1):  # typographic family, then family
        record = names.getName(name_id, 3, 1, 0x409) or names.getName(name_id, 1, 0, 0)
        if record:
            return record.toUnicode()
    return ""


def limit(memory, seconds):
    """Cap this process's memory and CPU time (no-op where the OS has no limits).

    Over the memory limit, Python raises MemoryError; over the CPU limit, the
    process is stopped. The parent also stops waiting after `seconds`.
    """
    if resource is None:
        return
    resource.setrlimit(resource.RLIMIT_AS, (memory, memory))
    resource.setrlimit(resource.RLIMIT_CPU, (seconds, seconds + 1))


def outcome(data, subset):
    """Convert, and say what happened: {"font": {...}}, {"refused": message},
    {"not_a_font": True} or {"too_complex": True}. Any other error is a bug."""
    try:
        return {"font": convert(data, subset)}
    except Refused as error:
        return {"refused": str(error)}
    except MemoryError:
        return {"too_complex": True}
    except PARSE_ERRORS:
        return {"not_a_font": True}


def work(answer, data, subset, memory, seconds):
    """The separate process: limit itself, convert, and send the outcome back.

    If something unexpected goes wrong, the process ends with its traceback on
    stderr (where the server's own error output goes) and sends nothing.
    """
    limit(memory, seconds)
    answer.send(outcome(data, subset))
    answer.close()
