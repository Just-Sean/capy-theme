"""Tests for site name, tagline and main logo (issue #10)."""

import io

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.urls import reverse
from PIL import Image

from capy_theme.active import activate
from capy_theme.admin import ThemeForm
from capy_theme.context_processors import theme as theme_context
from capy_theme.images import add_asset
from capy_theme.models import Theme
from capy_theme.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media_and_cache(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def png(name="logo.png", colour="red"):
    buffer = io.BytesIO()
    Image.new("RGB", (40, 20), colour).save(buffer, "PNG")
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


def render(source):
    return Template("{% load capy_theme %}" + source).render(Context({}))


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


def with_logo(theme, name="logo.png", colour="red"):
    """Upload a main logo for the theme and choose it (in the draft)."""
    asset = add_asset(theme, "logo_main", "light", png(name, colour))
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
    choices = ThemeForm(instance=theme).fields["image_logo_main_light"].choices
    assert [value for value, _ in choices] == ["", str(mine.pk)]


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


# {% theme_logo %}


def test_logo_tag_outputs_the_logo_with_alt_text():
    theme = live_theme(site_name="Capy Co", logo_alt="The Capy logo")
    asset = with_logo(theme)
    publish(theme)
    html = render('{% theme_logo class="h-8" %}')
    assert f'src="/media/{asset.original.name}"' in html
    assert 'alt="The Capy logo"' in html
    assert 'class="capy-logo h-8"' in html


def test_logo_alt_text_falls_back_to_the_site_name():
    theme = live_theme(site_name="Capy Co")
    with_logo(theme)
    publish(theme)
    assert 'alt="Capy Co"' in render("{% theme_logo %}")


def test_logo_tag_shows_the_site_name_without_a_logo():
    live_theme(site_name="Capy & Co")
    assert render('{% theme_logo class="font-bold" %}') == (
        '<span class="font-bold">Capy &amp; Co</span>'
    )


def test_logo_tag_outputs_nothing_without_logo_or_site_name():
    live_theme()
    assert render("{% theme_logo %}") == ""


def test_logo_tag_outputs_nothing_without_an_active_theme():
    assert render("{% theme_logo %}") == ""


def test_logo_tag_uses_published_values_not_the_draft():
    theme = live_theme(site_name="Published")
    theme.settings = {"site_name": "Draft"}
    theme.save()
    assert "Published" in render("{% theme_logo %}")


# Template context


def test_context_has_branding(rf):
    theme = live_theme(site_name="Capy Co", tagline="Hello")
    asset = with_logo(theme)
    publish(theme)
    values = theme_context(rf.get("/"))["theme"]
    assert values["site_name"] == "Capy Co"
    assert values["tagline"] == "Hello"
    assert values["logo_url"] == f"/media/{asset.original.name}"
    assert values["logo_alt"] == "Capy Co"


def test_admin_shows_branding_fields_and_read_only_settings(client, django_user_model):
    user = django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")
    client.force_login(user)
    theme = Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy Co"})
    content = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content
    assert b'name="site_name"' in content
    assert b'name="image_logo_main_light"' in content
    assert b'name="settings"' not in content  # no raw JSON box
    assert b"Stored settings" in content
