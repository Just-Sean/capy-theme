"""fontTools runs in its own process with memory and time limits (#191).

Fonts that are small but costly to read (glyphs packed with points) are refused
instead of using gigabytes or minutes, and fonts that break fontTools in any step
get "isn't a font", never a server error.
"""

import time

import pytest
from django.core.exceptions import ImproperlyConfigured, ValidationError

from capy_theme.fonts.uploads import prepare
from tests.support.fonts import many_points_font, self_calling_cff_font, ttf_bytes

MB = 1024 * 1024


@pytest.mark.parametrize("flavor", [None, "woff", "woff2"])
def test_a_font_over_the_memory_limit_is_refused(settings, flavor):
    """Well over 200 MB of points, against a 128 MB limit (the default is 512 MB)."""
    settings.CAPY_THEME_FONT_MAX_MEMORY_BYTES = 128 * MB
    with pytest.raises(ValidationError, match="too complex to process safely"):
        prepare(many_points_font(150, flavor), "points.ttf")


def test_a_font_over_the_time_limit_is_refused_on_time(settings):
    settings.CAPY_THEME_FONT_MAX_SECONDS = 1
    started = time.monotonic()
    with pytest.raises(ValidationError, match="too complex to process safely"):
        prepare(many_points_font(200), "points.ttf")
    assert time.monotonic() - started < 5


def test_a_font_under_the_limits_is_still_accepted(settings):
    settings.CAPY_THEME_FONT_MAX_MEMORY_BYTES = 128 * MB
    settings.CAPY_THEME_FONT_MAX_SECONDS = 5
    assert prepare(ttf_bytes(), "f.ttf")["file"].read()[:4] == b"wOF2"


@pytest.mark.parametrize("subset", ["all", "latin"])
def test_a_font_that_breaks_fonttools_when_saved_is_not_a_font(subset):
    """A subroutine calling itself fails only when the font is saved, not opened."""
    with pytest.raises(ValidationError, match="isn't a font"):
        prepare(self_calling_cff_font(), "loop.otf", subset)


@pytest.mark.parametrize(
    "name", ["CAPY_THEME_FONT_MAX_MEMORY_BYTES", "CAPY_THEME_FONT_MAX_SECONDS"]
)
@pytest.mark.parametrize("value", [0, None, "30"])
def test_the_limits_must_be_positive_whole_numbers(settings, name, value):
    setattr(settings, name, value)
    with pytest.raises(ImproperlyConfigured):
        prepare(ttf_bytes(), "f.ttf")
