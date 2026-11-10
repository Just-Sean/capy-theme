"""Tests for choosing a mode (the view and cookie) and the mode settings (issue #46)."""

import pytest
from django.core.cache import cache
from django.template import Context, Template
from django.urls import reverse

from capy_theme.admin.theme_form import ThemeForm
from capy_theme.context_processors import theme as theme_context
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.mode import COOKIE_MAX_AGE, COOKIE_NAME
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


def render(source, request):
    return Template("{% load capy_theme %}" + source).render(Context({"request": request}))


def get(rf, cookie=None):
    request = rf.get("/page/")
    if cookie:
        request.COOKIES[COOKIE_NAME] = cookie
    return request


def test_choosing_a_mode_sets_a_long_lived_cookie_and_goes_back(client):
    live()
    response = client.get(reverse("capy_theme:set_mode", args=["dark"]) + "?next=/somewhere/")
    assert response.status_code == 302
    assert response.url == "/somewhere/"
    cookie = response.cookies[COOKIE_NAME]
    assert cookie.value == "dark"
    assert cookie["max-age"] == COOKIE_MAX_AGE  # survives closing the browser
    assert cookie["samesite"] == "Lax"


def test_choosing_a_mode_wont_redirect_to_another_site(client):
    live()
    response = client.get(
        reverse("capy_theme:set_mode", args=["dark"]) + "?next=https://evil.example/"
    )
    assert response.url == "/"


def test_unknown_mode_is_not_found(client):
    live()
    assert client.get("/theme/mode/purple/").status_code == 404


def test_choice_isnt_saved_when_switching_is_off(client):
    live(visitors_can_switch=False)
    response = client.get(reverse("capy_theme:set_mode", args=["dark"]))
    assert COOKIE_NAME not in response.cookies


def test_cookie_changes_the_next_page(client):
    live()
    client.get(reverse("capy_theme:set_mode", args=["dark"]))
    html = Template("{% load capy_theme %}<html {% theme_html_attrs %}>").render(
        Context({"request": client.get("/admin/login/").wsgi_request})
    )
    assert 'data-theme="capy-dark"' in html


def form_data(**kwargs):
    data = {"name": "Main", "slug": "main", "light_base": "light", "dark_base": "dark"}
    return data | kwargs


def test_form_stores_only_non_default_mode_settings():
    form = ThemeForm(data=form_data(default_mode="auto", visitors_can_switch="on"))
    assert form.is_valid(), form.errors
    assert form.save().settings == {}

    form = ThemeForm(data=form_data(default_mode="dark"), instance=Theme.objects.get())
    assert form.is_valid(), form.errors
    assert form.save().settings == {"default_mode": "dark", "visitors_can_switch": False}


def test_form_shows_the_current_mode_settings():
    theme = Theme.objects.create(
        name="Main", slug="main", settings={"default_mode": "light", "visitors_can_switch": False}
    )
    form = ThemeForm(instance=theme)
    assert form.fields["default_mode"].initial == "light"
    assert form.fields["visitors_can_switch"].initial is False


def test_context_has_the_mode(rf):
    live(default_mode="dark")
    values = theme_context(get(rf, "light"))["theme"]
    assert values["default_mode"] == "dark"
    assert values["visitors_can_switch"] is True
    assert values["mode"] == "light"


def test_mode_settings_are_published_like_everything_else(rf):
    theme = live()
    theme.settings = {"default_mode": "dark"}
    theme.save()
    assert render("{% theme_html_attrs %}", get(rf)) == ""  # not published yet
    publish(theme)
    assert render("{% theme_html_attrs %}", get(rf)) == 'data-theme="capy-dark"'
