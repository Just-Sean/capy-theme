"""Tests for {% theme_head %}, {% theme_html_attrs %} and the theme context (issue #9)."""

import pytest
from django.core.cache import cache
from django.template import Context, Template

from capy_theme.active import activate
from capy_theme.context_processors import theme as theme_context
from capy_theme.models import Theme
from capy_theme.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def active_theme():
    theme = Theme.objects.create(name="Main", slug="main", light_base="cupcake")
    publish(theme)
    activate(theme)
    return theme


def render(source, request=None):
    return Template("{% load capy_theme %}" + source).render(Context({"request": request}))


def test_theme_head_links_the_active_stylesheet(active_theme, rf):
    html = render("{% theme_head %}", rf.get("/"))
    version = active_theme.live_revision.css_version
    assert html == f'<link rel="stylesheet" href="/theme/{version}.css">'


def test_theme_head_follows_publishing(active_theme, rf):
    active_theme.light_base = "emerald"
    active_theme.save()
    revision = publish(active_theme)
    assert revision.css_version in render("{% theme_head %}", rf.get("/"))


def test_theme_head_outputs_nothing_without_an_active_theme(rf):
    assert render("{% theme_head %}", rf.get("/")) == ""


def test_theme_head_works_without_a_request(active_theme):
    assert "<link" in render("{% theme_head %}")


def test_theme_html_attrs_outputs_nothing_yet(active_theme, rf):
    assert render("<html{% theme_html_attrs %}>", rf.get("/")) == "<html>"


def test_context_has_the_live_values(active_theme, rf):
    active_theme.light_base = "emerald"  # an unpublished draft change
    active_theme.save()
    theme = theme_context(rf.get("/"))["theme"]
    assert theme["name"] == "Main"
    assert theme["slug"] == "main"
    assert theme["revision"] == 1
    assert theme["light_base"] == "cupcake"  # the published value, not the draft
    assert theme["dark_base"] == "dark"
    assert theme["stylesheet_url"].endswith(".css")


def test_context_is_none_without_an_active_theme(rf):
    assert theme_context(rf.get("/")) == {"theme": None}


def test_context_reaches_every_template(active_theme, client, django_user_model):
    # The admin uses the project's templates settings, which include the processor.
    user = django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")
    client.force_login(user)
    response = client.get("/admin/")
    assert response.context["theme"]["name"] == "Main"
