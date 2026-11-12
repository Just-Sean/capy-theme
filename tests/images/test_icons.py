"""Tests for icons and favicons (issue #35)."""

import io

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.urls import reverse
from PIL import Image

from capy_theme.admin.theme_form import ThemeForm
from capy_theme.images.icons import FILES, icon_folder, icon_urls
from capy_theme.images.uploads import add_asset
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def square(color=(200, 0, 0, 255), size=600, transparent_border=False):
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0) if transparent_border else color)
    if transparent_border:
        image.paste(Image.new("RGBA", (size // 2, size // 2), color), (size // 4, size // 4))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return SimpleUploadedFile("icon.png", buffer.getvalue())


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


def with_icon(theme, icon_settings=None, dark=False, **upload):
    light = add_asset(theme, "icon", "light", square(**upload))
    chosen = {"light": light.pk}
    if dark:
        chosen["dark"] = add_asset(theme, "icon", "dark", square((20, 20, 20, 255))).pk
    theme.settings = {"images": {"icon": chosen}}
    if icon_settings:
        theme.settings["icon"] = icon_settings
    theme.save()
    revision = publish(theme)
    activate(theme)
    return revision


def read(revision, name):
    with default_storage.open(f"{icon_folder(revision.snapshot)}/{name}", "rb") as f:
        return f.read()


def opened(revision, name):
    return Image.open(io.BytesIO(read(revision, name)))


def test_publishing_makes_every_icon(theme):
    revision = with_icon(theme)
    for name in FILES:
        assert default_storage.exists(f"{icon_folder(revision.snapshot)}/{name}"), name
    assert opened(revision, "apple-touch-icon.png").size == (180, 180)
    assert opened(revision, "icon-192.png").size == (192, 192)
    assert opened(revision, "icon-512.png").size == (512, 512)
    assert opened(revision, "icon-maskable-512.png").size == (512, 512)
    ico = opened(revision, "favicon.ico")
    assert ico.format == "ICO"
    assert sorted(ico.info["sizes"]) == [(16, 16), (32, 32), (48, 48)]


def test_favicon_svg_switches_with_a_dark_icon(theme):
    svg = read(with_icon(theme, dark=True), "favicon.svg").decode()
    assert svg.count("data:image/png;base64,") == 2
    assert "prefers-color-scheme: dark" in svg
    Theme.objects.all().delete()
    other = Theme.objects.create(name="B", slug="b")
    svg = read(with_icon(other), "favicon.svg").decode()
    assert svg.count("data:image/png;base64,") == 1
    assert "prefers-color-scheme" not in svg


def test_background_and_padding(theme):
    revision = with_icon(theme, {"background": "#00ff00", "padding": 20}, color=(200, 0, 0, 255))
    icon = opened(revision, "icon-512.png").convert("RGBA")
    assert icon.getpixel((10, 10)) == (0, 255, 0, 255)  # padding shows the background
    assert icon.getpixel((256, 256)) == (200, 0, 0, 255)  # the icon in the middle


def test_transparent_by_default_but_home_screen_icons_are_solid(theme):
    revision = with_icon(theme, {"padding": 10})
    assert opened(revision, "icon-512.png").convert("RGBA").getpixel((5, 5))[3] == 0
    apple = opened(revision, "apple-touch-icon.png").convert("RGBA")
    assert apple.getpixel((2, 2)) == (255, 255, 255, 255)


def test_maskable_icon_keeps_the_icon_in_the_safe_zone(theme):
    revision = with_icon(theme)
    maskable = opened(revision, "icon-maskable-512.png").convert("RGBA")
    # The outer 10% is background; the icon is inside the middle 80%.
    assert maskable.getpixel((30, 30)) == (255, 255, 255, 255)
    assert maskable.getpixel((256, 256)) == (200, 0, 0, 255)
    assert maskable.getpixel((60, 256)) == (200, 0, 0, 255)


def test_monochrome_icon_is_white_in_the_icons_shape(theme):
    revision = with_icon(theme, transparent_border=True)
    mono = opened(revision, "icon-monochrome-512.png").convert("RGBA")
    assert mono.getpixel((256, 256)) == (255, 255, 255, 255)
    assert mono.getpixel((10, 10))[3] == 0


def test_the_issue_check_head_links(theme, rf):
    revision = with_icon(theme)
    urls = icon_urls(revision.snapshot)
    html = Template("{% load capy_theme %}{% theme_head %}").render(
        Context({"request": rf.get("/")})
    )
    assert f'<link rel="icon" href="{urls["favicon.ico"]}" sizes="32x32">' in html
    assert f'<link rel="icon" href="{urls["favicon.svg"]}" type="image/svg+xml">' in html
    assert f'<link rel="apple-touch-icon" href="{urls["apple-touch-icon.png"]}">' in html
    assert urls["favicon.ico"].startswith("/media/capy_theme/icons/")


def test_no_icon_no_links(theme, rf):
    publish(theme)
    activate(theme)
    html = Template("{% load capy_theme %}{% theme_head %}").render(
        Context({"request": rf.get("/")})
    )
    assert 'rel="icon"' not in html
    assert not default_storage.exists("capy_theme/icons")


def test_each_revision_keeps_its_icons(theme):
    first = with_icon(theme, {"padding": 0})
    theme.settings = {**theme.settings, "icon": {"padding": 15}}
    theme.save()
    second = publish(theme)
    assert icon_folder(first.snapshot) != icon_folder(second.snapshot)
    assert read(first, "icon-512.png") != read(second, "icon-512.png")
    # Publishing an unchanged icon (e.g. only colors changed) reuses the files.
    theme.settings = {**theme.settings, "site_name": "New"}
    theme.save()
    assert icon_folder(publish(theme).snapshot) == icon_folder(second.snapshot)


@pytest.mark.parametrize(
    "bad", [{"background": "red"}, {"padding": 30}, {"padding": -1}, {"other": 1}]
)
def test_bad_icon_settings_are_rejected(theme, bad):
    theme.settings = {"icon": bad}
    with pytest.raises(ValidationError):
        theme.save()


def test_admin_icon_fields(theme):
    asset = add_asset(theme, "icon", "light", square())
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
        "image_icon_light": str(asset.pk),
        "icon_background": "#FFFFFF",
        "icon_padding": "12",
    }
    form = ThemeForm(data=data, instance=theme)
    assert form.is_valid(), form.errors
    assert form.save().settings == {
        "images": {"icon": {"light": asset.pk}},
        "icon": {"background": "#ffffff", "padding": 12.0},
    }
    bad = ThemeForm(data=data | {"icon_background": "white"}, instance=theme)
    assert not bad.is_valid() and "icon_background" in bad.errors


def test_editor_offers_icon_controls(client, django_user_model, theme):
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    state = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert "icon" in [s["name"] for s in state["controls"]["logo_slots"]]
    assert [s["name"] for s in state["controls"]["icon_settings"]] == ["background", "padding"]
    asset = add_asset(theme, "icon", "light", square())
    changes = {"settings": {"images": {"icon": {"light": asset.pk}}, "icon": {"padding": 5}}}
    url = reverse("capy_theme:editor_save", args=[theme.pk])
    assert client.post(url, changes, content_type="application/json").status_code == 200
    theme.refresh_from_db()
    assert theme.settings["icon"] == {"padding": 5}
