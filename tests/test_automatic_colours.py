"""Tests for automatic text colours and background shades (issue #16)."""

import pytest
from coloraide import Color

from capy_theme.builtin_themes import THEMES
from capy_theme.colors import WITH_CONTENT, contrast, effective_values, readable_text, shade


def snapshot(light=None, base="light"):
    return {
        "light_values": dict(THEMES[base]["values"]),
        "dark_values": dict(THEMES["dark"]["values"]),
        "settings": {"colors": {"light": light or {}}},
    }


def lightness(value):
    return Color(value).convert("oklch")["lightness"]


DARK_BLUE = "oklch(25% 0.12 260)"
PALE_YELLOW = "oklch(92% 0.12 95)"


def test_the_issue_check_dark_primary_gets_light_text_and_vice_versa():
    on_dark = effective_values(snapshot({"primary": DARK_BLUE}), "light")["--color-primary-content"]
    on_light = effective_values(snapshot({"primary": PALE_YELLOW}), "light")[
        "--color-primary-content"
    ]
    assert lightness(on_dark) > 0.9
    assert lightness(on_light) < 0.3


@pytest.mark.parametrize("name", WITH_CONTENT)
def test_every_coloured_element_gets_readable_text(name):
    values = effective_values(snapshot({name: DARK_BLUE}), "light")
    assert contrast(values[f"--color-{name}-content"], DARK_BLUE) >= 7


@pytest.mark.parametrize(
    "background",
    [
        f"oklch({lightness}% {chroma} {hue})"
        for lightness in (5, 30, 55, 62, 70, 95)
        for chroma in (0, 0.15)
        for hue in (30, 140, 260)
    ],
)
def test_text_is_readable_on_any_colour(background):
    # WCAG AA for normal text needs 4.5:1. It's reached wherever white or black
    # can reach it; on the hardest mid-tones nothing does better than they do.
    best_possible = max(contrast("#fff", background), contrast("#000", background))
    assert contrast(readable_text(background), background) >= min(4.5, best_possible)


def test_a_text_colour_set_by_hand_is_kept():
    values = effective_values(
        snapshot({"primary": DARK_BLUE, "primary-content": "oklch(50% 0.2 30)"}), "light"
    )
    assert values["--color-primary-content"] == "oklch(50% 0.2 30)"


def test_text_colours_of_colours_not_overridden_come_from_the_base():
    values = effective_values(snapshot({"primary": DARK_BLUE}), "light")
    base = THEMES["light"]["values"]
    assert values["--color-secondary-content"] == base["--color-secondary-content"]


def test_background_shades_and_text_follow_an_overridden_background():
    values = effective_values(snapshot({"base-100": "oklch(96% 0.02 80)"}), "light")
    assert lightness(values["--color-base-200"]) < 0.96
    assert lightness(values["--color-base-300"]) < lightness(values["--color-base-200"])
    assert contrast(values["--color-base-content"], "oklch(96% 0.02 80)") >= 7


def test_shades_set_by_hand_are_kept():
    values = effective_values(
        snapshot({"base-100": "oklch(96% 0.02 80)", "base-200": "oklch(50% 0 0)"}), "light"
    )
    assert values["--color-base-200"] == "oklch(50% 0 0)"


def test_very_dark_backgrounds_get_lighter_shades():
    assert lightness(shade("oklch(3% 0 0)", 1)) > 0.03


def test_nothing_is_worked_out_without_overrides():
    assert effective_values(snapshot(), "light") == THEMES["light"]["values"]
