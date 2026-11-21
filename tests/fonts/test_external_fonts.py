"""Tests for external font stylesheets (issue #28)."""

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError

from capy_theme.artifacts.build import get_artifacts
from capy_theme.css.stylesheet import render_css
from capy_theme.editor.preview import preview
from capy_theme.fonts.library import external_stylesheets
from capy_theme.fonts.models import Font
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

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


def test_the_stylesheet_is_exposed_and_the_family_used():
    font = external()
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"heading": font.pk}})
    publish(theme)
    activate(theme)
    # The external stylesheet URL is exposed as data; the consumer links it itself.
    assert get_artifacts()["fonts"]["heading"]["stylesheet"] == KIT
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
