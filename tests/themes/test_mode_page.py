"""Tests for which mode a page uses, the toggle and the head script (issue #46)."""

import re

import pytest
from django.core.cache import cache
from django.template import Context, Template
from django.urls import reverse

from capy_theme.models import Theme
from capy_theme.themes.active import activate
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


def render(source, request):
    return Template("{% load capy_theme %}" + source).render(Context({"request": request}))


def get(rf, cookie=None):
    request = rf.get("/page/")
    if cookie:
        request.COOKIES[COOKIE_NAME] = cookie
    return request


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


def test_toggle_has_three_links_and_marks_the_current_mode(rf):
    live()
    html = render("{% theme_mode_toggle %}", get(rf, "dark"))
    for mode in ("light", "dark", "auto"):
        assert f'data-capy-mode="{mode}"' in html
        assert reverse("capy_theme:set_mode", args=[mode]) + "?next=/page/" in html
    assert (
        'data-capy-mode="dark" class="btn btn-sm join-item btn-active" aria-current="true"' in html
    )
    assert html.count('aria-current="true"') == 1
    assert "aria-pressed" not in html  # not allowed on links (issue #197)


def test_toggle_is_hidden_when_switching_is_off(rf):
    live(visitors_can_switch=False)
    assert render("{% theme_mode_toggle %}", get(rf)).strip() == ""


def test_toggle_is_hidden_without_an_active_theme(rf):
    assert render("{% theme_mode_toggle %}", get(rf)).strip() == ""


def test_head_script_applies_the_mode_before_the_page_draws(rf):
    live(default_mode="dark")
    html = render("{% theme_head %}", get(rf))
    script = html[html.index("<script>") :]
    assert f'n="{COOKIE_NAME}"' in script
    assert 'f="dark"' in script
    assert "s=true" in script
    assert "setAttribute('data-theme','capy-'+m)" in script
    # The toggle's current link is marked with aria-current, not aria-pressed (#197).
    assert "e.setAttribute('aria-current','true')" in script
    assert "aria-pressed" not in script


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


def test_head_script_and_csp_header_share_the_real_nonce(client, settings):
    # Issue #213: Django's real (lazy) nonce, with its CSP middleware. Before the
    # fix the script had no nonce and the header none either, so browsers blocked it.
    from django.utils.csp import CSP

    live()
    settings.MIDDLEWARE = [
        *settings.MIDDLEWARE,
        "django.middleware.csp.ContentSecurityPolicyMiddleware",
    ]
    settings.SECURE_CSP = {"script-src": [CSP.SELF, CSP.NONCE]}
    response = client.get("/page/")
    nonce = re.search(r"'nonce-([^']+)'", response["Content-Security-Policy"]).group(1)
    assert f'<script nonce="{nonce}">' in response.content.decode()
