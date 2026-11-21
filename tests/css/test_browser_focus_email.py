"""Tests for the focus color (in the stylesheet) and email colors (issue #20).

The theme-color meta tags used to be applied by {% theme_head %}; in v2 capy-theme only
exposes the colors (artifacts), and a consumer renders its own meta tags, so those tests
are gone. The base-100 color they checked is covered by the artifacts/colors tests.
"""

import pytest
from django.core.cache import cache

from capy_theme.artifacts.build import get_artifacts
from capy_theme.colors.color_math import contrast, focus_color, hex_colors
from capy_theme.css.stylesheet import render_css
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.catalog import THEMES
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


def live(**settings_values):
    theme = Theme.objects.create(name="Main", slug="main", settings=settings_values)
    publish(theme)
    activate(theme)
    return theme


# Focus outline


def test_focus_outline_rule_is_in_the_stylesheet():
    theme = Theme.objects.create(name="Main", slug="main")
    css = render_css(publish(theme))
    assert ":focus-visible {" in css
    assert "outline: 2px solid var(--capy-focus);" in css
    assert css.count("--capy-focus: ") == 4


def test_focus_uses_primary_when_it_stands_out():
    values = dict(THEMES["light"]["values"])
    assert focus_color(values) == values["--color-primary"]


def test_focus_falls_back_to_text_color_when_primary_is_too_faint():
    values = dict(THEMES["light"]["values"])
    values["--color-primary"] = "oklch(97% 0.01 90)"  # almost the same as the white background
    assert focus_color(values) == values["--color-base-content"]
    assert contrast(focus_color(values), values["--color-base-100"]) >= 3


# Email colors


def test_hex_colors_for_emails():
    colors = hex_colors(THEMES["light"]["values"])
    assert len(colors) == 20
    assert colors["base_100"] == "#ffffff"
    assert all(value.startswith("#") and len(value) == 7 for value in colors.values())


def test_artifacts_have_email_colors(rf):
    live(colors={"light": {"primary": "oklch(62.31% 0.188 259.81)"}})
    colors = get_artifacts(rf.get("/"))["colors_hex"]["light"]
    assert colors["primary"] == "#3b82f6"
