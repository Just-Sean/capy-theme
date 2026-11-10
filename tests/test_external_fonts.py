"""Tests for external font stylesheets (issue #28)."""

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.template import Context, Template

from capy_theme.active import activate
from capy_theme.editor import preview
from capy_theme.fonts import external_stylesheets
from capy_theme.models import Font, Theme
from capy_theme.publishing import publish
from capy_theme.stylesheet import render_css

pytestmark = pytest.mark.django_db
KIT = "https://use.typekit.net/abc1234.css"


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


def external(family="proxima-nova", url=KIT):
    font = Font(family=family, source="external", stylesheet_url=url, fallback_stack="sans-serif")
    font.full_clean()
    font.save()
    return font


def test_external_fonts_need_an_https_stylesheet():
    with pytest.raises(ValidationError, match="https://"):
        Font(
            family="X", source="external", stylesheet_url="http://insecure.example/x.css"
        ).full_clean()
    with pytest.raises(ValidationError, match="https://"):
        Font(family="Y", source="external").full_clean()


def test_other_fonts_cant_have_a_stylesheet():
    with pytest.raises(ValidationError, match="Only external fonts"):
        Font(family="Z", source="upload", stylesheet_url=KIT).full_clean()


def test_the_stylesheet_is_linked_and_the_family_used():
    font = external()
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"heading": font.pk}})
    publish(theme)
    activate(theme)
    request = __import__("django.test", fromlist=["RequestFactory"]).RequestFactory().get("/")
    head = Template("{% load capy_theme %}{% theme_head %}").render(Context({"request": request}))
    assert f'<link rel="stylesheet" href="{KIT}">' in head
    assert head.index(KIT) < head.index("/theme/")  # the font's stylesheet comes first
    css = render_css(theme.live_revision)
    assert '--capy-font-heading: "proxima-nova", sans-serif;' in css
    assert "@font-face" not in css  # the provider's stylesheet defines the faces


def test_each_stylesheet_once():
    font = external()
    fonts = {
        "body": {"source": "external", "stylesheet": KIT},
        "heading": {"source": "external", "stylesheet": KIT},
    }
    assert external_stylesheets(fonts) == [KIT]
    assert external_stylesheets({}) == []
    assert font.pk


def test_the_editor_gets_the_stylesheets_to_link():
    font = external()
    theme = Theme.objects.create(name="Main", slug="main")
    assert preview(theme, {"settings": {"fonts": {"body": font.pk}}})["stylesheets"] == [KIT]
