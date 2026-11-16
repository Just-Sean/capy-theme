"""Checking, converting and trimming font files (uploads and imports).

Any WOFF2, WOFF, TTF or OTF file is checked with fontTools (so a renamed image
is refused), converted to WOFF2, and optionally trimmed to one character subset.
fontTools runs in its own process with a memory and a time limit (`converting`),
because a small hostile font can otherwise use gigabytes or minutes (#191).
"""

import multiprocessing
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from .. import conf
from . import converting, unpacking
from .converting import PARSE_ERRORS, SUBSETS

SUBSET_CHOICES = [("all", "All characters (don't trim)")] + [
    (name, name.replace("-", " ").capitalize()) for name in SUBSETS
]

NOT_A_FONT = "That file isn't a font (WOFF2, WOFF, TTF or OTF)."
TOO_COMPLEX = (
    "The font is too complex to process safely (it needs more memory or time than "
    "the limits allow)."
)


def max_bytes():
    return conf.get("CAPY_THEME_FONT_MAX_BYTES")


def prepare(data, name, subset="all"):
    """Check a font file and return it as WOFF2, with what it says about itself.

    Returns {"file": ContentFile(woff2), "weight", "style", "family",
    "unicode_range"}. Raises ValidationError if it's too big or isn't a font, if
    trimming leaves no characters, or if it needs more memory or time than allowed.
    """
    if len(data) > max_bytes():
        raise ValidationError(
            f"The font file is too big ({len(data) // 1024} KB; the limit is "
            f"{max_bytes() // 1024} KB)."
        )
    try:
        unpacking.check(data)  # before fontTools unpacks anything (#191)
    except PARSE_ERRORS as error:
        raise ValidationError(NOT_A_FONT) from error
    outcome = _convert_in_own_process(data, subset)
    if "refused" in outcome:
        raise ValidationError(outcome["refused"])
    if "not_a_font" in outcome:
        raise ValidationError(NOT_A_FONT)
    if "too_complex" in outcome:
        raise ValidationError(TOO_COMPLEX)
    font = outcome["font"]
    font["file"] = ContentFile(font.pop("woff2"), name=f"{Path(name).stem}.woff2")
    return font


def _convert_in_own_process(data, subset):
    """Run `converting.work` in a new process under the limits; return its answer."""
    memory = conf.positive_int("CAPY_THEME_FONT_MAX_MEMORY_BYTES")
    seconds = conf.positive_int("CAPY_THEME_FONT_MAX_SECONDS")
    # "spawn" starts a fresh Python: safe in a threaded web server, unlike "fork".
    context = multiprocessing.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(
        target=converting.work, args=(sender, data, subset, memory, seconds), daemon=True
    )
    process.start()
    sender.close()
    try:
        if receiver.poll(seconds):
            return receiver.recv()
        return {"too_complex": True}  # still working after the time limit
    except EOFError:  # it ended without answering
        process.join()
        if process.exitcode < 0:  # stopped by the OS: over the CPU or memory limit
            return {"too_complex": True}
        raise RuntimeError("Font conversion failed; its traceback is on stderr.") from None
    finally:
        if process.is_alive():
            process.kill()
        process.join()
        receiver.close()
