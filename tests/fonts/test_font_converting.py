"""What the font process does, run directly here (#191).

`prepare()` runs `converting.work` in its own process, where coverage can't see
it, so its logic is also tested in this process (without the limits).
"""

import io
from pathlib import Path

import pytest
from fontTools.ttLib import TTFont

from capy_theme.fonts import converting
from tests.support.fonts import self_calling_cff_font, ttf_bytes


def test_a_font_is_converted_with_its_details():
    result = converting.outcome(ttf_bytes("My Serif", weight=700, italic=True), "all")["font"]
    assert result["woff2"][:4] == b"wOF2"
    assert (result["weight"], result["style"], result["family"]) == (700, "italic", "My Serif")


def test_a_subset_the_font_doesnt_have_is_refused():
    assert converting.outcome(ttf_bytes(), "greek") == {
        "refused": "The font has no greek characters."
    }


@pytest.mark.parametrize("data", [b"not a font", self_calling_cff_font()])
def test_anything_fonttools_fails_on_is_not_a_font(data):
    assert converting.outcome(data, "all") == {"not_a_font": True}


def test_running_out_of_memory_is_too_complex(monkeypatch):
    def out_of_memory(data, subset):
        raise MemoryError

    monkeypatch.setattr(converting, "convert", out_of_memory)
    assert converting.outcome(ttf_bytes(), "all") == {"too_complex": True}


class Pipe:
    def __init__(self):
        self.sent = []
        self.closed = False

    def send(self, value):
        self.sent.append(value)

    def close(self):
        self.closed = True


def test_work_limits_itself_then_sends_the_outcome(monkeypatch):
    limits = []
    monkeypatch.setattr(
        converting, "limit", lambda memory, seconds: limits.append((memory, seconds))
    )
    pipe = Pipe()
    converting.work(pipe, b"not a font", "all", 100, 5)
    assert limits == [(100, 5)]
    assert pipe.sent == [{"not_a_font": True}] and pipe.closed


def test_limit_sets_the_memory_and_cpu_limits(monkeypatch):
    calls = []

    class FakeResource:
        RLIMIT_AS, RLIMIT_CPU = "as", "cpu"

        @staticmethod
        def setrlimit(kind, values):
            calls.append((kind, values))

    monkeypatch.setattr(converting, "resource", FakeResource)
    converting.limit(100, 5)
    assert calls == [("as", (100, 100)), ("cpu", (5, 6))]


def test_without_os_limits_limit_does_nothing(monkeypatch):
    monkeypatch.setattr(converting, "resource", None)
    converting.limit(100, 5)  # no error


def test_trimming_keeps_only_the_subset():
    result = converting.outcome(ttf_bytes(), "latin")["font"]
    assert result["unicode_range"] == converting.SUBSETS["latin"]


GARAMOND = (
    Path(__file__).resolve().parents[2]
    / "src/capy_theme/static/capy_theme/fonts/eb-garamond/eb-garamond-latin-400-normal.woff2"
)


def damaged_layout_font():
    """EB Garamond as a TTF with one byte of its GPOS table changed (found by QA's fuzzing)."""
    font = TTFont(GARAMOND)
    font.flavor = None
    out = io.BytesIO()
    font.save(out)
    data = bytearray(out.getvalue())
    data[TTFont(io.BytesIO(bytes(data))).reader.tables["GPOS"].offset + 5297] = 168
    return bytes(data)


def test_a_damaged_layout_table_is_not_a_font_not_a_crash():
    # fontTools raises AttributeError for it while trimming (#251).
    assert converting.outcome(damaged_layout_font(), "latin") == {"not_a_font": True}
