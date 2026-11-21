"""Tests for the live editor's Components view (issues #155 and #158)."""

from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.template.loader import render_to_string
from django.urls import reverse

from capy_theme.editor.components_view import COMPONENTS
from capy_theme.models import Theme

pytestmark = pytest.mark.django_db
STATIC = Path(__file__).resolve().parents[2] / "src/capy_theme/static/capy_theme/editor"


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy"})


@pytest.fixture
def url(theme):
    return reverse("capy_theme:editor_components", args=[theme.pk])


@pytest.fixture
def editor_client(client, django_user_model):
    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    return client


def test_every_component_in_the_drafts_scheme(editor_client, url):
    response = editor_client.get(url)
    assert response.status_code == 200
    content = response.content.decode()
    # A theme is a single scheme now: the draft is a light theme, so only the light
    # block renders.
    assert content.count('data-theme="capy-light"') >= 1
    assert 'data-theme="capy-dark"' not in content
    for heading in (
        "Text",
        "Buttons",
        "Badges",
        "Alerts",
        "Cards",
        "Tabs",
        "Table",
        "Modal",
        "Images and icons",
    ):
        assert f'<h3 class="text-xl font-semibold">{heading}</h3>' in content, heading
    assert len(COMPONENTS) == 11
    # Its own daisyUI stylesheet, never the page being edited.
    assert "capy_theme/editor/components.css" in content


def test_ids_name_the_drafts_scheme(editor_client, url):
    content = editor_client.get(url).content.decode()
    # One scheme now: the light theme's modal has the light id, and there's no dark one.
    assert 'id="components-modal-light"' in content and 'id="components-modal-dark"' not in content


def test_only_framed_by_the_same_site(editor_client, url):
    assert editor_client.get(url)["X-Frame-Options"] == "SAMEORIGIN"


def test_needs_the_change_permission(client, django_user_model, url):
    assert client.get(url).status_code == 403
    client.force_login(django_user_model.objects.create_user("v", password="pw", is_staff=True))
    assert client.get(url).status_code == 403


def test_the_editor_knows_where_it_is(editor_client, theme, url):
    content = editor_client.get(f"/theme/live-edit/?edit={theme.pk}").content.decode()
    assert f'data-components-url="{url}"' in content
    assert "editor/controls/components.js" in content
    state = editor_client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert state["urls"]["components"] == url


def test_bundled_stylesheet_has_the_components():
    css = (STATIC / "components.css").read_text()
    for selector in (".btn", ".badge", ".alert", ".card", ".tab", ".table", ".modal", ".progress"):
        assert selector in css, selector


def test_the_page_has_nothing_a_strict_csp_would_block(editor_client, url):
    # #244: no inline handlers or style attributes.
    html = editor_client.get(url).content.decode()
    assert " style=" not in html
    assert " onsubmit=" not in html and " onclick=" not in html


def test_sample_fields_arent_a_form():
    # Enter in a sample field must never reload the page, so they're not in a <form> (#244).
    html = render_to_string("capy_theme/editor/components/forms.html", {"mode": "light"})
    assert "Form fields" in html and "<form" not in html


def test_radial_progress_value_comes_from_the_bundled_stylesheet(editor_client, url):
    assert "[--value:70]" in editor_client.get(url).content.decode()
    assert r".\[--value\:70\]{--value:70}" in (STATIC / "components.css").read_text()


def test_the_showcase_is_gone(client):
    assert client.get("/theme/showcase/").status_code == 404


def test_images_section_shows_the_saved_drafts_logos(editor_client, theme, url, settings, tmp_path):
    import io

    from django.core.files.uploadedfile import SimpleUploadedFile
    from PIL import Image

    from capy_theme.images.uploads import add_asset

    settings.MEDIA_ROOT = tmp_path
    buffer = io.BytesIO()
    Image.new("RGB", (300, 100), "red").save(buffer, "PNG")
    asset = add_asset(theme, "logo_main", SimpleUploadedFile("main.png", buffer.getvalue()))
    theme.settings = {**theme.settings, "images": {"logo_main": asset.pk}}
    theme.save()
    content = editor_client.get(url).content.decode()
    assert asset.original.name in content
    assert "Empty: falls back to the main logo" in content  # the stacked logo
    assert "made from the icon image when the theme is published" in content  # no icons yet
