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


def admin_data(upload, slot="logo_main", mode="light", alt="Logo"):
    """The theme page with a new image uploaded in a slot's own field (#271)."""
    name = f"image_{slot}_{mode}"
    return {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
        f"{name}_upload": upload,
        f"{name}_upload_alt": alt,  # the new image's own alt text box
        "assets-TOTAL_FORMS": "0",
        "assets-INITIAL_FORMS": "0",
        "revisions-TOTAL_FORMS": "0",
        "revisions-INITIAL_FORMS": "0",
    }


def test_admin_upload_strips_gps(admin_client, theme):
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    upload = SimpleUploadedFile("holiday.jpg", gps_photo(), content_type="image/jpeg")
    response = admin_client.post(url, admin_data(upload))
    assert response.status_code == 302
    asset = theme.assets.get()
    assert (asset.width, asset.height, asset.content_type) == (40, 20, "image/jpeg")
    assert asset.alt_text == "Logo"
    with asset.original.open("rb") as f:
        assert not Image.open(f).getexif()
    theme.refresh_from_db()
    assert theme.settings["images"] == {"logo_main": {"light": asset.pk}}  # chosen, no 2nd save
    assert b"40 \xc3\x97 20" in admin_client.get(url).content  # details shown


def test_admin_rejects_a_renamed_text_file(admin_client, theme):
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    upload = SimpleUploadedFile("logo.png", b"not an image", content_type="image/png")
    response = admin_client.post(url, admin_data(upload))
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


def test_admin_refuses_an_oversized_upload_before_reading_it(
    admin_client, theme, settings, monkeypatch
):
    # #253: the size is checked first, so a huge file is never read into memory.
    settings.CAPY_THEME_IMAGE_MAX_BYTES = 1024

    def must_not_read(*args, **kwargs):
        raise AssertionError("the upload was read")

    monkeypatch.setattr("capy_theme.images.uploads.prepare_image", must_not_read)
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    upload = SimpleUploadedFile("big.png", b"x" * 2048, content_type="image/png")
    response = admin_client.post(url, admin_data(upload))
    assert response.status_code == 200
    assert "The main logo is too big (2 KB; the limit is 1 KB)." in response.content.decode()
    assert not ThemeAsset.objects.exists()


# Admin uploads get the same copies as editor uploads (#254).


def png_upload(size):
    output = io.BytesIO()
    Image.new("RGB", size, (30, 90, 200)).save(output, "PNG")
    return SimpleUploadedFile("pic.png", output.getvalue(), content_type="image/png")


def test_a_header_logo_uploaded_in_the_admin_gets_its_smaller_copies(admin_client, theme):
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    response = admin_client.post(url, admin_data(png_upload((300, 100))))
    assert response.status_code == 302
    widths = set(theme.assets.get().variants.values_list("width", flat=True))
    assert {64, 128, 300} <= widths


def test_a_sharing_image_uploaded_in_the_admin_gets_its_1200_by_630_copy(admin_client, theme):
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    data = admin_data(png_upload((1300, 700)), slot="social")
    assert admin_client.post(url, data).status_code == 302
    sharing = theme.assets.get().variants.get(purpose="social")
    assert (sharing.width, sharing.height) == (1200, 630)
