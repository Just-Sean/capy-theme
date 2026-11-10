"""Tests for the web app manifest (issue #36)."""

import io

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.urls import reverse
from PIL import Image

from capy_theme.active import activate
from capy_theme.admin import ThemeForm
from capy_theme.builtin_themes import THEMES
from capy_theme.colors import to_hex
from capy_theme.icons import icon_urls
from capy_theme.images import add_asset
from capy_theme.models import Theme
from capy_theme.publishing import publish

pytestmark = pytest.mark.django_db
URL = "/theme/manifest.webmanifest"


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def live(settings_values, icon=False):
    theme = Theme.objects.create(name="Admin label", slug="main", settings=settings_values)
    if icon:
        buffer = io.BytesIO()
        Image.new("RGB", (512, 512), "red").save(buffer, "PNG")
        asset = add_asset(theme, "icon", "light", SimpleUploadedFile("i.png", buffer.getvalue()))
        theme.settings = {**theme.settings, "images": {"icon": {"light": asset.pk}}}
        theme.save()
    revision = publish(theme)
    activate(theme)
    return revision


def test_manifest_from_the_theme(client):
    revision = live(
        {
            "site_name": "Capy Coffee",
            "tagline": "Good coffee",
            "app": {"short_name": "Capy", "display": "minimal-ui", "orientation": "portrait"},
        },
        icon=True,
    )
    response = client.get(URL)
    assert response.status_code == 200
    assert response["Content-Type"] == "application/manifest+json"
    data = response.json()
    base = to_hex(THEMES["light"]["values"]["--color-base-100"], alpha=False)
    urls = icon_urls(revision.snapshot)
    assert data == {
        "id": "/",
        "name": "Capy Coffee",
        "short_name": "Capy",
        "description": "Good coffee",
        "start_url": "/",
        "scope": "/",
        "display": "minimal-ui",
        "orientation": "portrait",
        "background_color": base,
        "theme_color": base,
        "icons": [
            {"src": urls["icon-192.png"], "sizes": "192x192", "type": "image/png"},
            {"src": urls["icon-512.png"], "sizes": "512x512", "type": "image/png"},
            {
                "src": urls["icon-maskable-512.png"],
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
            {
                "src": urls["icon-monochrome-512.png"],
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "monochrome",
            },
        ],
    }


def test_app_settings_win_over_site_name_and_tagline(client):
    live(
        {
            "site_name": "Site",
            "tagline": "Tag",
            "app": {"name": "The App", "description": "Desc", "start_url": "/app/"},
        }
    )
    data = client.get(URL).json()
    assert (data["name"], data["short_name"], data["description"]) == ("The App", "The App", "Desc")
    assert data["start_url"] == data["id"] == "/app/"
    assert data["display"] == "standalone"
    assert "orientation" not in data  # any
    assert data["icons"] == []


def test_dark_default_mode_uses_dark_colours(client):
    live({"default_mode": "dark"})
    dark = to_hex(THEMES["dark"]["values"]["--color-base-100"], alpha=False)
    assert client.get(URL).json()["background_color"] == dark


def test_uses_the_published_revision_not_the_draft(client):
    live({"site_name": "Published"})
    theme = Theme.objects.get()
    theme.settings = {"site_name": "Draft"}
    theme.save()
    assert client.get(URL).json()["name"] == "Published"


def test_no_active_theme_is_404(client):
    assert client.get(URL).status_code == 404


def test_theme_head_links_the_manifest(rf):
    live({})
    html = Template("{% load capy_theme %}{% theme_head %}").render(
        Context({"request": rf.get("/")})
    )
    assert f'<link rel="manifest" href="{reverse("capy_theme:manifest")}">' in html


@pytest.mark.parametrize(
    "bad",
    [
        {"start_url": "https://evil.example/"},
        {"start_url": "//evil.example/"},
        {"short_name": "Thirteen chars"},
        {"display": "window"},
        {"colour": "red"},
    ],
)
def test_bad_app_settings_are_rejected(bad):
    theme = Theme.objects.create(name="T", slug="t")
    theme.settings = {"app": bad}
    with pytest.raises(ValidationError):
        theme.save()


def test_admin_web_app_fields():
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
        "app_name": " Capy ",
        "app_display": "fullscreen",
        "app_start_url": "/start/",
    }
    form = ThemeForm(data=data)
    assert form.is_valid(), form.errors
    assert form.save().settings == {
        "app": {"name": "Capy", "display": "fullscreen", "start_url": "/start/"}
    }
    bad = ThemeForm(data=data | {"slug": "b", "app_start_url": "https://x.example/"})
    assert not bad.is_valid() and "app_start_url" in bad.errors


def test_editor_saves_app_settings(client, django_user_model):
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    theme = Theme.objects.create(name="Main", slug="main")
    state = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    names = [s["name"] for s in state["controls"]["app_settings"]]
    assert names == ["name", "short_name", "description", "start_url", "display", "orientation"]
    url = reverse("capy_theme:editor_save", args=[theme.pk])
    changes = {"settings": {"app": {"name": "Capy", "display": "browser"}}}
    assert client.post(url, changes, content_type="application/json").status_code == 200
    theme.refresh_from_db()
    assert theme.settings["app"] == {"name": "Capy", "display": "browser"}
