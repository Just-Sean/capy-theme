"""Tests for palette suggestions (issue #18)."""

import io
import json

import pytest
from coloraide import Color
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image, ImageDraw

from capy_theme.models import Theme
from capy_theme.palette import from_logo, from_primary

pytestmark = pytest.mark.django_db


def hue(value):
    return Color(value).convert("oklch")["hue"]


def logo_bytes():
    image = Image.new("RGBA", (200, 100), (255, 255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 120, 100], fill=(220, 38, 38))  # red, largest
    draw.rectangle([120, 0, 170, 100], fill=(37, 99, 235))  # blue
    draw.rectangle([170, 0, 200, 100], fill=(250, 204, 21))  # yellow, smallest
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    return buffer.getvalue()


def test_three_suggestions_from_a_primary_colour():
    result = from_primary("#3b82f6")
    assert [s["name"] for s in result] == ["Analogous", "Complementary", "Triadic"]
    for suggestion in result:
        assert set(suggestion["colors"]) == {"secondary", "accent", "neutral"}


def test_complementary_is_the_opposite_hue():
    complementary = from_primary("oklch(60% 0.2 100)")[1]
    assert round(hue(complementary["colors"]["secondary"])) == 280


def test_logo_colours_most_used_first_ignoring_white():
    suggestion = from_logo(io.BytesIO(logo_bytes()))
    colors = suggestion["colors"]
    assert set(colors) == {"primary", "secondary", "accent", "neutral"}
    assert 15 < hue(colors["primary"]) < 40  # red
    assert 250 < hue(colors["secondary"]) < 275  # blue
    assert 80 < hue(colors["accent"]) < 105  # yellow


def test_logo_without_colour_gives_no_suggestion():
    image = Image.new("RGB", (50, 50), (255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, "PNG")
    assert from_logo(io.BytesIO(buffer.getvalue())) is None


def test_broken_file_gives_no_suggestion():
    assert from_logo(io.BytesIO(b"not an image")) is None


@pytest.fixture
def editor_client(client, django_user_model):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename="change_theme")
    )
    client.force_login(user)
    return client


def post(client, theme, data):
    return client.post(
        reverse("capy_theme:editor_suggestions", args=[theme.pk]),
        data=json.dumps(data),
        content_type="application/json",
    )


def test_endpoint_gives_logo_and_primary_suggestions(editor_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    theme = Theme.objects.create(name="Main", slug="main")
    theme.logo = SimpleUploadedFile("logo.png", logo_bytes(), content_type="image/png")
    theme.save()
    response = post(editor_client, theme, {"primary": "#3b82f6"})
    assert response.status_code == 200
    names = [s["name"] for s in response.json()["suggestions"]]
    assert names == ["From your logo", "Analogous", "Complementary", "Triadic"]


def test_endpoint_without_logo(editor_client):
    theme = Theme.objects.create(name="Main", slug="main")
    names = [
        s["name"] for s in post(editor_client, theme, {"primary": "red"}).json()["suggestions"]
    ]
    assert names == ["Analogous", "Complementary", "Triadic"]


def test_endpoint_rejects_a_bad_colour(editor_client):
    theme = Theme.objects.create(name="Main", slug="main")
    assert post(editor_client, theme, {"primary": "nope"}).status_code == 400


def test_endpoint_saves_nothing(editor_client):
    theme = Theme.objects.create(name="Main", slug="main")
    post(editor_client, theme, {"primary": "red"})
    assert Theme.objects.get(pk=theme.pk).settings == {}


def test_endpoint_needs_permission(client, django_user_model):
    client.force_login(django_user_model.objects.create_user("v", password="pw", is_staff=True))
    theme = Theme.objects.create(name="Main", slug="main")
    assert post(client, theme, {"primary": "red"}).status_code == 403
