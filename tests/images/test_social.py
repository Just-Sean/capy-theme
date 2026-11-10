"""Tests for the social sharing image (issue #37; tags removed in #143)."""

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
from capy_theme.images.sharing import sharing_image
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


def picture(size=(1600, 1600), fmt="JPEG", mode="RGB", colour="red"):
    buffer = io.BytesIO()
    Image.new(mode, size, colour).save(buffer, fmt)
    return SimpleUploadedFile(f"share.{fmt.lower()}", buffer.getvalue())


def live(settings_values=None, image=None, alt=""):
    theme = Theme.objects.create(name="T", slug="t", settings=settings_values or {})
    if image is not None:
        asset = add_asset(theme, "social", "light", image, alt)
        theme.settings = {**theme.settings, "images": {"social": {"light": asset.pk}}}
        theme.save()
    revision = publish(theme)
    activate(theme)
    return revision


def head(rf, source="{% theme_head %}", path="/about/"):
    return Template("{% load capy_theme %}" + source).render(Context({"request": rf.get(path)}))


# The image


def test_sharing_image_is_cropped_to_1200_by_630():
    revision = live(image=picture((1600, 1600)))
    image = sharing_image(revision.snapshot)
    assert (image["width"], image["height"]) == (1200, 630)
    with default_storage.open(image["file"], "rb") as f:
        stored = Image.open(f)
        assert stored.size == (1200, 630)
        assert stored.format == "JPEG"


def test_transparent_parts_become_white():
    revision = live(image=picture((1300, 700), "PNG", "RGBA", (0, 0, 0, 0)))
    with default_storage.open(sharing_image(revision.snapshot)["file"], "rb") as f:
        stored = Image.open(f)
        assert stored.format == "PNG"
        assert stored.convert("RGB").getpixel((600, 315)) == (255, 255, 255)


def test_svg_isnt_accepted_for_sharing():
    theme = Theme.objects.create(name="T", slug="t")
    svg = SimpleUploadedFile("s.svg", b'<svg xmlns="http://www.w3.org/2000/svg"/>')
    with pytest.raises(ValidationError, match="Upload a PNG or JPEG"):
        add_asset(theme, "social", "light", svg)


# No tags: link-preview tags belong to the project or another module (#143)


def test_theme_head_outputs_no_link_preview_tags(rf):
    live({"site_name": "Capy", "tagline": "Hello"}, image=picture())
    html = head(rf)
    assert "og:" not in html and "twitter:" not in html
    assert 'rel="manifest"' not in html


# Controls


def test_admin_sharing_image_field():
    theme = Theme.objects.create(name="T", slug="t")
    asset = add_asset(theme, "social", "light", picture())
    data = {
        "name": "T",
        "slug": "t",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
        "image_social_light": str(asset.pk),
    }
    form = ThemeForm(data=data, instance=theme)
    assert "image_social_dark" not in form.fields
    assert "social_description" not in form.fields
    assert form.is_valid(), form.errors
    assert form.save().settings == {"images": {"social": {"light": asset.pk}}}


def test_editor_offers_the_sharing_image_slot(client, django_user_model):
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    theme = Theme.objects.create(name="T", slug="t")
    state = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    slots = {s["name"]: s["modes"] for s in state["controls"]["logo_slots"]}
    assert slots["social"] == ["light"]
    assert "social_settings" not in state["controls"]
    assert "app_settings" not in state["controls"]


def test_old_app_and_social_settings_are_rejected():
    theme = Theme.objects.create(name="T", slug="t")
    for key in ("app", "social"):
        theme.settings = {key: {"description": "x"}}
        with pytest.raises(ValidationError):
            theme.save()
