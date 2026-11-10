"""Tests for device accessibility preferences (issue #49)."""

import pytest

from capy_theme.css.stylesheet import render_css
from capy_theme.models import Theme
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture
def css():
    return render_css(publish(Theme.objects.create(name="A", slug="a")))


def block(css, query):
    return css.split(query, 1)[1].split("\n}", 1)[0]


def test_reduce_motion_stops_animations_and_transitions(css):
    rules = block(css, "@media (prefers-reduced-motion: reduce) {")
    assert "*, *::before, *::after {" in rules
    assert "animation-duration: 0.01ms !important;" in rules
    assert "transition-duration: 0.01ms !important;" in rules
    assert "scroll-behavior: auto !important;" in rules


def test_more_contrast_removes_noise_and_depth_and_thickens_borders(css):
    rules = block(css, "@media (prefers-contrast: more) {")
    assert "--noise: 0 !important;" in rules
    assert "--depth: 0 !important;" in rules
    assert "--border: 2px !important;" in rules
    assert "outline-width: 3px;" in rules


def test_the_rules_come_after_the_theme_values(css):
    # So they win over the theme's own --noise, --depth and --border.
    assert css.index("@media (prefers-contrast: more)") > css.index('[data-theme="capy-dark"]')
