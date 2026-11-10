"""Tests for the editor's "See it as a visitor" view and summary (issue #158)."""

from datetime import UTC, datetime

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.urls import reverse

from capy_theme.css.stylesheet import render_css
from capy_theme.models import Theme, ThemeAssignment
from capy_theme.themes.active import activate, theme_at
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
URL = "/theme/editor/visitor-view/"


@pytest.fixture(autouse=True)
def clear():
    cache.clear()
    yield
    cache.clear()


def published(name, **fields):
    theme = Theme.objects.create(name=name, slug=name.lower(), **fields)
    publish(theme)
    return theme


@pytest.fixture
def site():
    main = published("Main", settings={"default_mode": "dark"})
    activate(main)
    holiday = published("Holiday", light_base="valentine")
    ThemeAssignment.objects.create(
        theme=holiday,
        starts_at=datetime(2099, 12, 1, tzinfo=UTC),
        ends_at=datetime(2099, 12, 26, tzinfo=UTC),
    )
    ocean = published("Ocean", light_base="cupcake", offered_to_visitors=True)
    return {"main": main, "holiday": holiday, "ocean": ocean}


@pytest.fixture
def editor_client(client, django_user_model):
    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    return client


def test_the_issue_check_visitors_see_the_published_theme(editor_client, site):
    body = editor_client.get(URL).json()
    assert body["theme"] == "Main"
    assert body["css"] == render_css(site["main"].live_revision)


def test_the_issue_check_a_date_inside_a_schedule(editor_client, site):
    body = editor_client.get(URL, {"date": "2099-12-10"}).json()
    assert body["theme"] == "Holiday"
    assert editor_client.get(URL, {"date": "2099-12-27"}).json()["theme"] == "Main"


def test_an_offered_theme(editor_client, site):
    assert editor_client.get(URL, {"theme": "ocean"}).json()["theme"] == "Ocean"
    response = editor_client.get(URL, {"theme": "holiday"})  # not offered
    assert response.status_code == 400


def test_a_bad_date(editor_client, site):
    assert editor_client.get(URL, {"date": "10/12/2099"}).status_code == 400


def test_the_summary(editor_client, site):
    summary = editor_client.get(URL).json()["summary"]
    assert summary["live_theme"] == "Main"
    assert summary["default_mode"] == "Dark"
    assert summary["can_switch"] is True
    assert summary["offered"] == [{"slug": "ocean", "name": "Ocean"}]
    assert [s["theme"] for s in summary["schedule"]] == ["Holiday"]
    assert summary["schedule"][0]["running"] is False


def test_the_editor_state_has_the_summary_and_url(editor_client, site):
    state = editor_client.get(reverse("capy_theme:editor_state", args=[site["main"].pk])).json()
    assert state["visitors"]["live_theme"] == "Main"
    assert state["urls"]["visitor_view"] == URL


def test_needs_the_change_permission(client, site):
    assert client.get(URL).status_code == 403


def test_theme_at_uses_the_same_rules_as_the_site(site):
    assert theme_at(datetime(2099, 12, 5, tzinfo=UTC)) == site["holiday"]
    assert theme_at(datetime(2099, 11, 5, tzinfo=UTC)) == site["main"]


def test_the_controls_are_loaded(editor_client, site):
    content = editor_client.get(f"/page/?edit={site['main'].pk}").content.decode()
    assert "editor/controls/visitor.js" in content
    assert f'data-visitor-view-url="{URL}"' in content
