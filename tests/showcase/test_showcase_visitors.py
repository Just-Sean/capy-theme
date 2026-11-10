"""Tests for the showcase's mode and visitor choices (issue #50)."""

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.utils import timezone

from capy_theme.models import Theme, ThemeAssignment
from capy_theme.themes.active import activate
from capy_theme.themes.mode import COOKIE_NAME
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
URL = "/theme/showcase/"


@pytest.fixture(autouse=True)
def clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff(client, django_user_model):
    client.force_login(django_user_model.objects.create_user("s", password="pw", is_staff=True))
    return client


def published(name, **fields):
    theme = Theme.objects.create(name=name, slug=name.lower(), **fields)
    publish(theme)
    return theme


def panel(content):
    return content.split("data-capy-showcase-visitors", 1)[1].split("</section>", 1)[0]


def test_panel_shows_mode_settings_and_the_toggle(staff):
    activate(published("Site", settings={"default_mode": "dark"}))
    html = panel(staff.get(URL).content.decode())
    assert "Default mode: <strong>Dark</strong>" in html
    assert "Visitors can switch" in html
    assert 'data-capy-mode="light"' in html


def test_the_issue_check_switching_mode_applies_site_wide(staff):
    activate(published("Site"))
    html = panel(staff.get(URL).content.decode())
    assert "/theme/mode/dark/?next=/theme/showcase/" in html
    staff.get("/theme/mode/dark/?next=/theme/showcase/")
    assert staff.cookies[COOKIE_NAME].value == "dark"
    assert staff.cookies[COOKIE_NAME]["path"] == "/"  # every page, not just the showcase
    # Any other page of the site reads the same cookie.
    from django.template import Context, Template
    from django.test import RequestFactory

    other_page = RequestFactory().get("/some/other/page/")
    other_page.COOKIES[COOKIE_NAME] = staff.cookies[COOKIE_NAME].value
    html = Template("{% load capy_theme %}<html {% theme_html_attrs %}>").render(
        Context({"request": other_page})
    )
    assert 'data-theme="capy-dark"' in html


def test_no_toggle_when_visitors_cant_switch(staff):
    activate(published("Site", settings={"visitors_can_switch": False}))
    html = panel(staff.get(URL).content.decode())
    assert "Visitors can't switch" in html
    assert "data-capy-mode" not in html


def test_picker_in_the_showcase(staff, settings):
    activate(published("Site"))
    published("Ocean", offered_to_visitors=True)
    html = panel(staff.get(URL).content.decode())
    assert "1 offered" in html
    assert 'data-capy-theme-choice="ocean"' in html
    settings.CAPY_THEME_VISITOR_THEMES = False
    html = panel(staff.get(URL).content.decode())
    assert "turned off" in html and "data-capy-theme-choice" not in html


def test_the_issue_check_scheduled_themes_with_dates(staff):
    activate(published("Site"))
    holiday = published("Holiday")
    now = timezone.now()
    ThemeAssignment.objects.create(
        theme=holiday, starts_at=now + timedelta(days=10), ends_at=now + timedelta(days=20)
    )
    sale = published("Sale")
    ThemeAssignment.objects.create(theme=sale, starts_at=now - timedelta(days=1))
    finished = published("Finished")
    ThemeAssignment.objects.create(theme=finished, ends_at=now - timedelta(days=1))
    html = panel(staff.get(URL).content.decode())
    assert html.count("data-capy-schedule") == 2
    assert "Holiday" in html and "Sale" in html and "Finished" not in html
    start = timezone.localtime(now + timedelta(days=10)).strftime("%Y-%m-%d %H:%M")
    assert start in html
    assert "Running" in html and "Upcoming" in html


def test_without_a_theme(staff):
    html = panel(staff.get(URL).content.decode())
    assert "Scheduled themes" in html
    assert "None. Add one in the admin" in html
