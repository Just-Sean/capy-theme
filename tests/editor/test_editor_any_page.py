"""Tests for editing on any page (issue #43)."""

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.template import Context, Template

from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def active():
    theme = Theme.objects.create(name="Main", slug="main")
    publish(theme)
    activate(theme)
    return theme


def user_with(django_user_model, *codenames, staff=True):
    user = django_user_model.objects.create_user("u", password="pw", is_staff=staff)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename__in=codenames)
    )
    return django_user_model.objects.get(pk=user.pk)


def head(rf, user=None, query=""):
    request = rf.get("/any-page/" + query)
    if user is not None:
        request.user = user
    return Template("{% load capy_theme %}{% theme_head %}").render(Context({"request": request}))


def test_editors_get_the_editor_on_any_page(rf, django_user_model, active):
    html = head(rf, user_with(django_user_model, "change_theme"))
    assert '<script id="capy-editor"' in html
    assert "editor/controls/core.js" in html
    assert 'data-floating-button="true"' in html
    assert 'data-theme-name="Main"' in html


def test_visitors_and_other_staff_dont(rf, django_user_model, active):
    from django.contrib.auth.models import AnonymousUser

    assert "capy-editor" not in head(rf, AnonymousUser())
    assert "capy-editor" not in head(rf, user_with(django_user_model, "view_theme"))
    assert "capy-editor" not in head(rf)  # no auth middleware at all


def test_non_staff_with_permission_dont(rf, django_user_model, active):
    assert "capy-editor" not in head(rf, user_with(django_user_model, "change_theme", staff=False))


def test_edit_parameter_works_on_any_page(rf, django_user_model, active):
    other = Theme.objects.create(name="Other", slug="other")
    html = head(rf, user_with(django_user_model, "change_theme"), f"?edit={other.pk}")
    assert 'data-theme-name="Other"' in html


def test_editor_works_without_an_active_theme_when_editing_one(rf, django_user_model):
    theme = Theme.objects.create(name="Draft", slug="draft")
    html = head(rf, user_with(django_user_model, "change_theme"), f"?edit={theme.pk}")
    assert 'data-theme-name="Draft"' in html


def test_corner_button_can_be_turned_off(rf, django_user_model, active, settings):
    settings.CAPY_THEME_EDITOR_BUTTON = False
    html = head(rf, user_with(django_user_model, "change_theme"))
    assert 'data-floating-button="false"' in html


def test_showcase_has_one_editor(client, django_user_model, active):
    client.force_login(user_with(django_user_model, "change_theme"))
    content = client.get("/theme/showcase/").content.decode()
    assert content.count('id="capy-editor"') == 1
    assert "data-capy-editor-open" in content
