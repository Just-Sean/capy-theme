"""Tests for light/dark mode settings and the toggle (issue #46)."""

import pytest
from django.core.cache import cache
from django.template import Context, Template
from django.urls import reverse

from capy_theme.active import activate
from capy_theme.admin import ThemeForm
from capy_theme.context_processors import theme as theme_context
from capy_theme.mode import COOKIE_MAX_AGE, COOKIE_NAME
from capy_theme.models import Theme
from capy_theme.publishing import publish

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


# Which mode a page uses ({% theme_html_attrs %})


def test_default_is_auto_and_follows_the_device(rf):
    live()
    assert render("{% theme_html_attrs %}", get(rf)) == ""


@pytest.mark.parametrize("mode", ["light", "dark"])
def test_theme_default_mode_forces_a_mode(rf, mode):
    live(default_mode=mode)
    assert render("{% theme_html_attrs %}", get(rf)) == f'data-theme="capy-{mode}"'


def test_visitor_choice_wins_over_the_default(rf):
    live(default_mode="dark")
    assert render("{% theme_html_attrs %}", get(rf, "light")) == 'data-theme="capy-light"'
    assert render("{% theme_html_attrs %}", get(rf, "auto")) == ""


def test_visitor_choice_is_ignored_when_switching_is_off(rf):
    live(default_mode="dark", visitors_can_switch=False)
    assert render("{% theme_html_attrs %}", get(rf, "light")) == 'data-theme="capy-dark"'


def test_unknown_cookie_value_is_ignored(rf):
    live(default_mode="dark")
    assert render("{% theme_html_attrs %}", get(rf, "purple")) == 'data-theme="capy-dark"'


def test_no_attributes_without_an_active_theme(rf):
    assert render("{% theme_html_attrs %}", get(rf, "dark")) == ""


# {% theme_mode_toggle %}


def test_toggle_has_three_links_and_marks_the_current_mode(rf):
    live()
    html = render("{% theme_mode_toggle %}", get(rf, "dark"))
    for mode in ("light", "dark", "auto"):
        assert f'data-capy-mode="{mode}"' in html
        assert reverse("capy_theme:set_mode", args=[mode]) + "?next=/page/" in html
    assert (
        'data-capy-mode="dark" class="btn btn-sm join-item btn-active" aria-pressed="true"' in html
    )
    assert html.count('aria-pressed="true"') == 1


def test_toggle_is_hidden_when_switching_is_off(rf):
    live(visitors_can_switch=False)
    assert render("{% theme_mode_toggle %}", get(rf)).strip() == ""


def test_toggle_is_hidden_without_an_active_theme(rf):
    assert render("{% theme_mode_toggle %}", get(rf)).strip() == ""


# The script in {% theme_head %}


def test_head_script_applies_the_mode_before_the_page_draws(rf):
    live(default_mode="dark")
    html = render("{% theme_head %}", get(rf))
    script = html[html.index("<script>") :]
    assert f'n="{COOKIE_NAME}"' in script
    assert 'f="dark"' in script
    assert "s=true" in script
    assert "setAttribute('data-theme','capy-'+m)" in script


def test_head_script_knows_when_switching_is_off(rf):
    live(visitors_can_switch=False)
    assert "s=false" in render("{% theme_head %}", get(rf))


def test_head_script_carries_the_csp_nonce(rf):
    live()
    request = get(rf)
    request._csp_nonce = "abc123"  # what Django's CSP middleware sets
    assert '<script nonce="abc123">' in render("{% theme_head %}", request)


def test_head_script_has_no_nonce_without_csp(rf):
    live()
    assert "<script>" in render("{% theme_head %}", get(rf))


# The view behind the toggle links (used without JavaScript)


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


# Admin form and template context


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
