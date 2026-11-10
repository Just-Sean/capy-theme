"""Tests for the theme showcase page (issue #11)."""

from pathlib import Path

import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse

from capy_theme.models import Theme
from capy_theme.showcase.views import SHOWCASE_SECTIONS
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db

URL = "/theme/showcase/"
SHOWCASE_CSS = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "capy_theme"
    / "static"
    / "capy_theme"
    / "showcase.css"
)


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff(client, django_user_model):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    client.force_login(user)
    return client


@pytest.fixture
def live():
    theme = Theme.objects.create(
        name="Main",
        slug="main",
        light_base="cupcake",
        dark_base="dracula",
        settings={"site_name": "Capy Co", "tagline": "Lorem tagline"},
    )
    publish(theme)
    activate(theme)
    return theme


def test_url_name():
    assert reverse("capy_theme:showcase") == URL


# Who can see it


def test_staff_can_see_it_by_default(staff):
    assert staff.get(URL).status_code == 200


def test_logged_out_visitors_are_sent_to_log_in(client):
    response = client.get(URL)
    assert response.status_code == 302
    assert response.url.startswith(reverse("admin:login"))


def test_logged_in_non_staff_are_sent_to_log_in(client, django_user_model):
    client.force_login(django_user_model.objects.create_user("visitor", password="pw"))
    assert client.get(URL).status_code == 302


def test_public_lets_anyone_see_it(client, settings):
    settings.CAPY_THEME_SHOWCASE = "public"
    assert client.get(URL).status_code == 200


def test_off_hides_it_from_everyone(staff, settings):
    settings.CAPY_THEME_SHOWCASE = "off"
    assert staff.get(URL).status_code == 404


def test_unknown_setting_is_an_error(staff, settings):
    settings.CAPY_THEME_SHOWCASE = "everyone"
    with pytest.raises(ImproperlyConfigured, match="CAPY_THEME_SHOWCASE"):
        staff.get(URL)


# What it shows


def test_shows_the_active_theme_in_light_and_dark(staff, live):
    content = staff.get(URL).content.decode()
    assert "Active theme: <strong>Main</strong>, revision 1" in content
    assert "<strong>cupcake</strong>" in content
    assert "<strong>dracula</strong>" in content
    assert 'data-theme="capy-light"' in content
    assert 'data-theme="capy-dark"' in content
    assert "Capy Co" in content
    assert "Lorem tagline" in content
    # The theme's stylesheet is linked, so the capy-light/capy-dark rules apply.
    assert live.live_revision.css_version in content


def test_every_section_appears_in_both_modes(staff, live):
    response = staff.get(URL)
    used = [t.name for t in response.templates]
    for name in SHOWCASE_SECTIONS:
        assert used.count(f"capy_theme/showcase/sections/{name}.html") == 2, name


def test_shows_every_component_from_the_issue(staff, live):
    content = staff.get(URL).content.decode()
    for marker in [
        "btn-primary",
        "btn-xs",
        "btn-xl",
        "badge-accent",
        "alert-error",
        'class="card',
        "tabs",
        "<table",
        "input",
        "select",
        "textarea",
        "checkbox",
        "toggle",
        "modal",
        "progress",
        "<h1",
        "<h6",
        "<ul",
        "<ol",
        "link",
        "<pre",
    ]:
        assert marker in content, marker


def test_publishing_changes_the_showcase(staff, live):
    live.light_base = "emerald"
    live.save()
    publish(live)
    content = staff.get(URL).content.decode()
    assert "<strong>emerald</strong>" in content
    assert "revision 2" in content


def test_without_an_active_theme_it_uses_daisyui_defaults(staff):
    content = staff.get(URL).content.decode()
    assert "No theme is active" in content
    assert 'data-theme="light"' in content
    assert 'data-theme="dark"' in content


def test_standalone_page_by_default(staff, live):
    response = staff.get(URL)
    assert "capy_theme/showcase/standalone.html" in [t.name for t in response.templates]
    assert "capy_theme/showcase.css" in response.content.decode()


def test_uses_the_projects_base_template_when_set(staff, live, settings, tmp_path):
    (tmp_path / "project_base.html").write_text(
        "<html><body><nav>PROJECT NAV</nav>{% block content %}{% endblock %}</body></html>"
    )
    settings.TEMPLATES = [
        {**settings.TEMPLATES[0], "DIRS": [tmp_path]},
    ]
    settings.CAPY_THEME_BASE_TEMPLATE = "project_base.html"
    response = staff.get(URL)
    content = response.content.decode()
    assert "PROJECT NAV" in content
    assert "Theme showcase" in content
    assert "capy_theme/showcase/standalone.html" not in [t.name for t in response.templates]


# The bundled stylesheet


def test_bundled_stylesheet_has_daisyui_and_layout_classes():
    css = SHOWCASE_CSS.read_text(encoding="utf-8")
    assert "daisyUI" in css
    for selector in [".btn{", ".modal{", ".tabs-lift", "xl\\:grid-cols-2", "[data-theme=dark]"]:
        assert selector in css, selector
    assert SHOWCASE_CSS.stat().st_size < 200_000  # trimmed, not daisyUI's 1 MB file
