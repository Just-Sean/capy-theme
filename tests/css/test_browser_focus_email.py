"""Tests for browser colour, focus colour and email colours (issue #20)."""

import pytest
from django.core.cache import cache
from django.template import Context, Template

from capy_theme.colors.maths import contrast, focus_color, hex_colors, to_hex
from capy_theme.context_processors import theme as theme_context
from capy_theme.css.stylesheet import render_css
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.catalogue import THEMES
from capy_theme.themes.mode import COOKIE_NAME
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


def head(rf, cookie=None):
    request = rf.get("/")
    if cookie:
        request.COOKIES[COOKIE_NAME] = cookie
    return Template("{% load capy_theme %}{% theme_head %}").render(Context({"request": request}))


# theme-color


def test_theme_color_follows_the_device_with_one_tag_per_mode(rf):
    live()
    html = head(rf)
    light = to_hex(THEMES["light"]["values"]["--color-base-100"], alpha=False)
    dark = to_hex(THEMES["dark"]["values"]["--color-base-100"], alpha=False)
    assert (
        f'<meta name="theme-color" media="(prefers-color-scheme: light)" content="{light}">' in html
    )
    assert (
        f'<meta name="theme-color" media="(prefers-color-scheme: dark)" content="{dark}">' in html
    )


def test_theme_color_uses_an_overridden_background(rf):
    live(colors={"light": {"base-100": "oklch(97.5% 0.026 90.1)"}})
    expected = to_hex("oklch(97.5% 0.026 90.1)", alpha=False)
    assert f'media="(prefers-color-scheme: light)" content="{expected}"' in head(rf)


def test_forced_mode_gives_a_single_theme_color(rf):
    live()
    html = head(rf, cookie="dark")
    dark = to_hex(THEMES["dark"]["values"]["--color-base-100"], alpha=False)
    assert html.count('name="theme-color"') == 1
    assert f'<meta name="theme-color" content="{dark}">' in html


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


def test_focus_falls_back_to_text_colour_when_primary_is_too_faint():
    values = dict(THEMES["light"]["values"])
    values["--color-primary"] = "oklch(97% 0.01 90)"  # almost the same as the white background
    assert focus_color(values) == values["--color-base-content"]
    assert contrast(focus_color(values), values["--color-base-100"]) >= 3


# Email colours


def test_hex_colors_for_emails():
    colors = hex_colors(THEMES["light"]["values"])
    assert len(colors) == 20
    assert colors["base_100"] == "#ffffff"
    assert all(value.startswith("#") and len(value) == 7 for value in colors.values())


def test_context_has_email_colours(rf):
    live(colors={"light": {"primary": "oklch(62.31% 0.188 259.81)"}})
    colors = theme_context(rf.get("/"))["theme"]["email_colors"]
    assert colors["primary"] == "#3b82f6"
