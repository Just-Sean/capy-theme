"""Tests for who gets the live editor, which theme it edits, and its state (issue #42)."""

from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.urls import reverse

from capy_theme.editor.access import can_edit, can_publish
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
PAGE = "/page/"  # an ordinary project page with {% theme_head %} (tests/urls.py)
PINK = "oklch(65% 0.24 350)"
STATIC = Path(__file__).resolve().parents[2] / "src/capy_theme/static/capy_theme/editor"


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


def staff_user(django_user_model, *codenames):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename__in=codenames)
    )
    return django_user_model.objects.get(pk=user.pk)  # fresh, so permissions aren't cached


@pytest.fixture
def editor_client(client, django_user_model):
    client.force_login(staff_user(django_user_model, "view_theme", "change_theme"))
    return client


@pytest.fixture
def active():
    theme = Theme.objects.create(name="Main", slug="main")
    publish(theme)
    activate(theme)
    return theme


def state_url(theme):
    return reverse("capy_theme:editor_state", args=[theme.pk])


# Who can edit


def test_staff_with_change_permission_can_edit(django_user_model):
    user = staff_user(django_user_model, "change_theme")
    assert can_edit(user)
    assert not can_publish(user)


def test_staff_without_change_permission_cant(django_user_model):
    assert not can_edit(staff_user(django_user_model, "view_theme"))


def test_editors_get_the_editor(editor_client, active):
    content = editor_client.get(PAGE).content.decode()
    assert 'id="capy-editor"' in content
    assert "capy_theme/editor/editor.js" in content
    assert f'data-state-url="{state_url(active)}"' in content


def test_no_editor_without_permission(client, django_user_model, active):
    client.force_login(staff_user(django_user_model, "view_theme"))
    content = client.get(PAGE).content.decode()
    assert 'id="capy-editor"' not in content
    assert "editor.js" not in content


def test_no_editor_without_a_theme(editor_client):
    assert 'id="capy-editor"' not in editor_client.get(PAGE).content.decode()


def test_edit_parameter_picks_another_theme(editor_client, active):
    other = Theme.objects.create(name="Other", slug="other")
    content = editor_client.get(f"{PAGE}?edit={other.pk}").content.decode()
    assert f'data-state-url="{state_url(other)}"' in content
    assert 'data-theme-name="Other"' in content


# The state endpoint


def test_state_has_the_draft_and_its_css(editor_client, active):
    active.settings = {"colors": {"light": {"primary": PINK}}}
    active.save()
    response = editor_client.get(state_url(active))
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    data = response.json()
    assert data["name"] == "Main"
    assert data["settings"]["colors"]["light"]["primary"] == PINK
    assert f"--color-primary: {PINK};" in data["css"]
    assert data["live_revision"] == 1
    assert data["has_unpublished_changes"] is True
    assert data["can_publish"] is False


def test_state_css_matches_publishing(editor_client, active):
    from capy_theme.css.stylesheet import render_css

    data = editor_client.get(state_url(active)).json()
    published = render_css(active.live_revision)
    # Same rules; only the comment line differs.
    assert data["css"].splitlines()[1:] == published.splitlines()[1:]


def test_state_is_refused_without_permission(client, django_user_model, active):
    client.force_login(staff_user(django_user_model, "view_theme"))
    assert client.get(state_url(active)).status_code == 403
    client.logout()
    assert client.get(state_url(active)).status_code == 403


def test_viewing_the_state_changes_nothing(editor_client, active):
    before = Theme.objects.get(pk=active.pk).updated_at
    editor_client.get(state_url(active))
    assert Theme.objects.get(pk=active.pk).updated_at == before


def test_visitors_dont_get_the_editor(client, settings, active):
    settings.CAPY_THEME_PAGE = "public"
    assert "editor.js" not in client.get(PAGE).content.decode()


# The bundled files


def test_editor_files_are_bundled():
    script = (STATIC / "editor.js").read_text()
    assert "adoptedStyleSheets" in script
    assert "data-capy-editor-open" in script
    assert ".capy-editor" in (STATIC / "editor.css").read_text()
