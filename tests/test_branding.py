"""Tests for site name, tagline and main logo (issue #10)."""

import io

import pytest
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.urls import reverse
from PIL import Image

from capy_theme.active import activate
from capy_theme.admin import ThemeForm
from capy_theme.context_processors import theme as theme_context
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


def test_form_accepts_a_logo_image():
    form = ThemeForm(data=form_data(), files={"logo": png()})
    assert form.is_valid(), form.errors
    theme = form.save()
    assert theme.logo.name.startswith("capy_theme/logos/")
    assert default_storage.exists(theme.logo.name)


def test_form_rejects_a_file_that_isnt_an_image():
    fake = SimpleUploadedFile("logo.png", b"not an image", content_type="image/png")
    form = ThemeForm(data=form_data(), files={"logo": fake})
    assert not form.is_valid()
    assert "logo" in form.errors


# Publishing


def test_revision_keeps_its_logo_after_the_logo_is_replaced():
    theme = Theme.objects.create(name="Main", slug="main", logo=png("first.png"))
    first = publish(theme)
    theme.logo = png("second.png", "blue")
    theme.save()
    second = publish(theme)
    assert first.snapshot["logo"] != second.snapshot["logo"]
    assert default_storage.exists(first.snapshot["logo"])  # old file not overwritten
    assert default_storage.exists(second.snapshot["logo"])


def test_changing_branding_is_an_unpublished_change():
    theme = live_theme()
    theme.settings = {"site_name": "New"}
    theme.save()
    assert theme.has_unpublished_changes


# {% theme_logo %}


def test_logo_tag_outputs_the_logo_with_alt_text():
    theme = live_theme(site_name="Capy Co", logo_alt="The Capy logo")
    theme.logo = png()
    theme.save()
    publish(theme)
    html = render('{% theme_logo class="h-8" %}')
    assert html == (f'<img src="/media/{theme.logo.name}" alt="The Capy logo" class="h-8">')


def test_logo_alt_text_falls_back_to_the_site_name():
    theme = live_theme(site_name="Capy Co")
    theme.logo = png()
    theme.save()
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
    theme.logo = png()
    theme.save()
    publish(theme)
    values = theme_context(rf.get("/"))["theme"]
    assert values["site_name"] == "Capy Co"
    assert values["tagline"] == "Hello"
    assert values["logo_url"] == f"/media/{theme.logo.name}"
    assert values["logo_alt"] == "Capy Co"


def test_admin_shows_branding_fields_and_read_only_settings(client, django_user_model):
    user = django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")
    client.force_login(user)
    theme = Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy Co"})
    content = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content
    assert b'name="site_name"' in content
    assert b'name="logo"' in content
    assert b'name="settings"' not in content  # no raw JSON box
    assert b"Stored settings" in content
