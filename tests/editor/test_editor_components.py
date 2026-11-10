"""Tests for the live editor's Components view (issue #155)."""

from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from capy_theme.editor.views import COMPONENTS
from capy_theme.models import Theme

pytestmark = pytest.mark.django_db
URL = "/theme/editor/components/"
STATIC = Path(__file__).resolve().parents[2] / "src/capy_theme/static/capy_theme/editor"


@pytest.fixture
def editor_client(client, django_user_model):
    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    return client


def test_every_component_in_light_and_dark(editor_client):
    response = editor_client.get(URL)
    assert response.status_code == 200
    content = response.content.decode()
    assert content.count('data-theme="capy-light"') >= 1
    assert content.count('data-theme="capy-dark"') >= 1
    for heading in ("Text", "Buttons", "Badges", "Alerts", "Cards", "Tabs", "Table", "Modal"):
        assert f'<h3 class="text-xl font-semibold">{heading}</h3>' in content, heading
    assert len(COMPONENTS) == 10
    # Its own daisyUI stylesheet, never the page being edited.
    assert "capy_theme/editor/components.css" in content


def test_ids_differ_between_light_and_dark(editor_client):
    content = editor_client.get(URL).content.decode()
    assert 'id="components-modal-light"' in content and 'id="components-modal-dark"' in content


def test_only_framed_by_the_same_site(editor_client):
    assert editor_client.get(URL)["X-Frame-Options"] == "SAMEORIGIN"


def test_needs_the_change_permission(client, django_user_model):
    assert client.get(URL).status_code == 403
    client.force_login(django_user_model.objects.create_user("v", password="pw", is_staff=True))
    assert client.get(URL).status_code == 403


def test_the_editor_knows_where_it_is(editor_client):
    theme = Theme.objects.create(name="Main", slug="main")
    content = editor_client.get(f"/page/?edit={theme.pk}").content.decode()
    assert f'data-components-url="{reverse("capy_theme:editor_components")}"' in content
    assert "editor/controls/components.js" in content
    state = editor_client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert state["urls"]["components"] == URL


def test_bundled_stylesheet_has_the_components():
    css = (STATIC / "components.css").read_text()
    for selector in (".btn", ".badge", ".alert", ".card", ".tab", ".table", ".modal", ".progress"):
        assert selector in css, selector


def test_the_showcase_is_gone(client):
    assert client.get("/theme/showcase/").status_code == 404
