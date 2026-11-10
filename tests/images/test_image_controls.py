"""Tests for uploading images in the admin and the live editor (issue #32)."""

import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import ExifTags, Image, PngImagePlugin

from capy_theme.images.models import ThemeAsset
from capy_theme.images.slots import SLOTS
from capy_theme.models import Theme

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


def gps_photo(orientation=None, size=(40, 20)):
    """A JPEG with camera details and a GPS location in its EXIF."""
    image = Image.new("RGB", size, (200, 30, 30))
    exif = image.getexif()
    exif[ExifTags.Base.Make] = "Spy Camera"
    if orientation:
        exif[ExifTags.Base.Orientation] = orientation
    gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
    gps[ExifTags.GPS.GPSLatitudeRef] = "N"
    gps[ExifTags.GPS.GPSLatitude] = (51.0, 30.0, 0.0)
    buffer = io.BytesIO()
    image.save(buffer, "JPEG", exif=exif)
    return buffer.getvalue()


def png(size=(10, 10), text=None, mode="RGBA"):
    info = PngImagePlugin.PngInfo()
    if text:
        info.add_text("Comment", text)
    buffer = io.BytesIO()
    Image.new(mode, size, (0, 128, 255, 255) if mode == "RGBA" else 0).save(
        buffer, "PNG", pnginfo=info
    )
    return buffer.getvalue()


def reopen(clean):
    return Image.open(io.BytesIO(clean["file"].read()))


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


@pytest.fixture
def admin_client(client, django_user_model):
    client.force_login(django_user_model.objects.create_superuser("sean", "s@example.com", "pw"))
    return client


def admin_data(**files):
    return {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
        "assets-TOTAL_FORMS": "1",
        "assets-INITIAL_FORMS": "0",
        "assets-0-slot": "logo_main",
        "assets-0-mode": "light",
        "assets-0-alt_text": "Logo",
        "revisions-TOTAL_FORMS": "0",
        "revisions-INITIAL_FORMS": "0",
    } | files


def test_admin_upload_strips_gps(admin_client, theme):
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    upload = SimpleUploadedFile("holiday.jpg", gps_photo(), content_type="image/jpeg")
    response = admin_client.post(url, admin_data(**{"assets-0-original": upload}))
    assert response.status_code == 302
    asset = theme.assets.get()
    assert (asset.width, asset.height, asset.content_type) == (40, 20, "image/jpeg")
    with asset.original.open("rb") as f:
        assert not Image.open(f).getexif()
    assert b"40 \xc3\x97 20" in admin_client.get(url).content  # details shown, read-only


def test_admin_rejects_a_renamed_text_file(admin_client, theme):
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    upload = SimpleUploadedFile("logo.png", b"not an image", content_type="image/png")
    response = admin_client.post(url, admin_data(**{"assets-0-original": upload}))
    assert response.status_code == 200
    assert "supported image" in response.content.decode()
    assert not ThemeAsset.objects.exists()


@pytest.fixture
def editor_client(client, django_user_model):
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    return client


def upload_url(theme):
    return reverse("capy_theme:editor_upload", args=[theme.pk])


def test_editor_upload(editor_client, theme):
    upload = SimpleUploadedFile("holiday.jpg", gps_photo(), content_type="image/jpeg")
    response = editor_client.post(
        upload_url(theme), {"slot": "icon", "mode": "light", "alt_text": "", "file": upload}
    )
    assert response.status_code == 200, response.content
    body = response.json()
    assert body["uploaded"]["slot"] == "icon"
    assert [a["id"] for a in body["assets"]] == [theme.assets.get().pk]
    state = editor_client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert state["assets"][0]["url"].startswith("/media/capy_theme/assets/icon/")
    assert "upload" in state["urls"]
    assert {s["name"] for s in state["controls"]["image_slots"]} == set(SLOTS)


def test_editor_rejects_a_renamed_text_file(editor_client, theme):
    upload = SimpleUploadedFile("logo.png", b"hello", content_type="image/png")
    response = editor_client.post(upload_url(theme), {"slot": "icon", "file": upload})
    assert response.status_code == 400
    assert "supported image" in response.json()["errors"][0]
    assert not ThemeAsset.objects.exists()


def test_editor_upload_needs_a_file(editor_client, theme):
    assert editor_client.post(upload_url(theme), {"slot": "icon"}).status_code == 400


def test_editor_upload_needs_permission(client, django_user_model, theme):
    client.force_login(django_user_model.objects.create_user("v", password="pw", is_staff=True))
    upload = SimpleUploadedFile("a.png", png())
    assert client.post(upload_url(theme), {"slot": "icon", "file": upload}).status_code == 403
    assert not ThemeAsset.objects.exists()
