"""Tests for the type scale and font loading (issue #29)."""

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.template import Context, Template
from django.test import RequestFactory

from capy_theme.active import activate
from capy_theme.admin import ThemeForm
from capy_theme.editor import controls
from capy_theme.fonts import preload_urls
from capy_theme.models import Font, FontFile, Theme
from capy_theme.publishing import publish
from capy_theme.stylesheet import render_css
from capy_theme.typography import MINIMUM_BASE_SIZE, heading_sizes, type_css

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def setup(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def test_heading_sizes_follow_the_scale():
    sizes = heading_sizes(1.25)
    assert sizes["h6"] == 1
    assert sizes["h5"] == 1.25
    assert sizes["h1"] == round(1.25**5, 4)


def test_type_css():
    css = "\n".join(
        type_css(
            {"type": {"base_size": 18, "scale": 1.2, "line_height": 1.6, "heading_weight": 600}}
        )
    )
    assert "--capy-base-size: 18px;" in css
    assert "html { font-size: var(--capy-base-size); }" in css
    assert "--capy-h1: 2.4883rem;" in css
    assert "body { line-height: var(--capy-line-height); }" in css
    assert "h1, h2, h3, h4, h5, h6 { font-weight: var(--capy-heading-weight); }" in css
    assert "@layer base {" in css
    assert type_css({}) == []


def test_the_issue_check_base_size_scales_the_page():
    theme = Theme.objects.create(name="Main", slug="main", settings={"type": {"base_size": 20}})
    css = render_css(publish(theme))
    assert "--capy-base-size: 20px;" in css


def test_the_issue_check_base_size_has_a_minimum():
    assert MINIMUM_BASE_SIZE == 14
    with pytest.raises(ValidationError):
        Theme.objects.create(name="Small", slug="small", settings={"type": {"base_size": 10}})
    form = ThemeForm(
        data={
            "name": "Main",
            "slug": "main",
            "light_base": "light",
            "dark_base": "dark",
            "visitors_can_switch": "on",
            "type_base_size": "10",
        }
    )
    assert not form.is_valid()
    assert "type_base_size" in form.errors


def test_admin_form_stores_type_settings():
    form = ThemeForm(
        data={
            "name": "Main",
            "slug": "main",
            "light_base": "light",
            "dark_base": "dark",
            "visitors_can_switch": "on",
            "type_base_size": "17.5",
            "type_heading_weight": "700",
        }
    )
    assert form.is_valid(), form.errors
    assert form.save().settings == {"type": {"base_size": 17.5, "heading_weight": 700}}


def font_with(family, files):
    font = Font.objects.create(family=family, source="upload")
    for weight, style, subset in files:
        f = FontFile(font=font, weight=weight, style=style, subset=subset)
        f.file.save(f"{family}-{weight}-{style}-{subset}.woff2", ContentFile(b"wOF2"), save=True)
    return font


def test_preload_picks_the_regular_latin_file_of_body_and_heading():
    body = font_with(
        "Body",
        [
            (700, "normal", "latin"),
            (400, "italic", "latin"),
            (400, "normal", "cyrillic"),
            (400, "normal", "latin"),
        ],
    )
    heading = font_with("Head", [(700, "normal", "latin")])
    theme = Theme.objects.create(
        name="Main", slug="main", settings={"fonts": {"body": body.pk, "heading": heading.pk}}
    )
    revision = publish(theme)
    urls = preload_urls(revision.snapshot["fonts"])
    assert urls == [
        body.files.get(weight=400, style="normal", subset="latin").file.url,
        heading.files.get().file.url,
    ]
    activate(theme)
    head = Template("{% load capy_theme %}{% theme_head %}").render(
        Context({"request": RequestFactory().get("/")})
    )
    assert f'<link rel="preload" href="{urls[0]}" as="font" type="font/woff2" crossorigin>' in head


def test_no_preload_for_system_fonts():
    sans = Font.objects.get(family="System sans")
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"body": sans.pk}})
    assert preload_urls(publish(theme).snapshot["fonts"]) == []


def test_editor_offers_type_controls():
    names = [item["name"] for item in controls()["type"]]
    assert names == ["base_size", "scale", "line_height", "heading_weight"]
    base = controls()["type"][0]
    assert (base["min"], base["unit"]) == (14, "px")
