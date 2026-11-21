"""Tests for site name, tagline and main logo (issue #10)."""

import io

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from capy_theme.admin.theme_form import ThemeForm
from capy_theme.artifacts.build import get_artifacts
from capy_theme.images.uploads import add_asset
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_and_cache(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def png(name="logo.png", color="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), color).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def form_data(**kwargs):
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",  # ticked by default in the real form
    }
    return data | kwargs


def live_theme(**settings_values):
    theme = Theme.objects.create(name="Main", slug="main", settings=settings_values)
    publish(theme)
    activate(theme)
    return theme


# The admin form


def test_form_stores_branding_in_settings():
    form = ThemeForm(data=form_data(site_name="Capy Co", tagline="Hello", logo_alt="Capy logo"))
    assert form.is_valid(), form.errors
    theme = form.save()
    assert theme.settings == {"site_name": "Capy Co", "tagline": "Hello", "logo_alt": "Capy logo"}


def test_form_shows_current_values_and_blank_removes_them():
    theme = Theme.objects.create(name="Main", slug="main", settings={"site_name": "Old"})
    assert ThemeForm(instance=theme).fields["site_name"].initial == "Old"
    form = ThemeForm(data=form_data(site_name="  "), instance=theme)
    assert form.is_valid(), form.errors
    assert form.save().settings == {}


def with_logo(theme, name="logo.png", color="red"):
    """Upload a main logo for the theme and choose it (in the draft)."""
    asset = add_asset(theme, "logo_main", "light", png(name, color))
    theme.settings = {**theme.settings, "images": {"logo_main": {"light": asset.pk}}}
    theme.save()
    return asset


def test_form_chooses_the_main_logo():
    theme = Theme.objects.create(name="Main", slug="main")
    asset = add_asset(theme, "logo_main", "light", png())
    form = ThemeForm(data=form_data(image_logo_main_light=str(asset.pk)), instance=theme)
    assert form.is_valid(), form.errors
    assert form.save().settings == {"images": {"logo_main": {"light": asset.pk}}}


def test_form_only_offers_this_themes_images_for_the_slot():
    theme = Theme.objects.create(name="Main", slug="main")
    other = Theme.objects.create(name="Other", slug="other")
    mine = add_asset(theme, "logo_main", "light", png())
    add_asset(theme, "logo_mark", "light", png())
    add_asset(other, "logo_main", "light", png())
    choices = ThemeForm(instance=theme).fields["image_logo_main_light"].widget.choices
    assert [str(value) for value, _ in choices] == ["", str(mine.pk)]


# Publishing


def test_revision_keeps_its_logo_after_the_logo_is_replaced():
    theme = Theme.objects.create(name="Main", slug="main")
    with_logo(theme, "first.png")
    first = publish(theme)
    with_logo(theme, "second.png", "blue")
    second = publish(theme)
    old = first.snapshot["images"]["logo_main"]["light"]["file"]
    new = second.snapshot["images"]["logo_main"]["light"]["file"]
    assert old != new
    assert default_storage.exists(old)  # old file not overwritten
    assert default_storage.exists(new)


def test_a_theme_cant_choose_another_themes_image():
    other = Theme.objects.create(name="Other", slug="other")
    asset = add_asset(other, "logo_main", "light", png())
    theme = Theme.objects.create(name="Main", slug="main")
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    with pytest.raises(ValidationError, match="isn't one of this theme's"):
        theme.save()


def test_changing_branding_is_an_unpublished_change():
    theme = live_theme()
    theme.settings = {"site_name": "New"}
    theme.save()
    assert theme.has_unpublished_changes


# Artifacts (data for consumers)


def test_artifacts_have_branding(rf):
    theme = live_theme(site_name="Capy Co", tagline="Hello")
    asset = with_logo(theme)
    publish(theme)
    artifacts = get_artifacts(rf.get("/"))
    assert artifacts["branding"]["site_name"] == "Capy Co"
    assert artifacts["branding"]["tagline"] == "Hello"
    assert artifacts["branding"]["logo_alt"] == "Capy Co"
    assert artifacts["logos"]["logo_main"]["light"]["url"].endswith(f"/media/{asset.original.name}")


def test_admin_shows_branding_fields_and_read_only_settings(client, django_user_model):
    user = django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")
    client.force_login(user)
    theme = Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy Co"})
    content = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content
    assert b'name="site_name"' in content
    assert b'name="image_logo_main_light"' in content
    assert b'name="settings"' not in content  # no raw JSON box
    assert b"Stored settings" in content
