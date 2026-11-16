"""Tests for the theme admin's Export button and Import theme page (issue #54)."""

import io
import json
import zipfile

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from capy_theme.models import Theme
from capy_theme.portability.export import export_theme

pytestmark = pytest.mark.django_db
IMPORT = "/admin/capy_theme/theme/import/"


def staff(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user("s", password="pw", is_staff=True)
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    client.force_login(user)
    return client


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy"})


def test_export_button_and_download(client, django_user_model, theme):
    staff(client, django_user_model, "view_theme")
    page = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content.decode()
    export_url = reverse("admin:capy_theme_theme_export", args=[theme.pk])
    assert f'href="{export_url}">Export</a>' in page
    response = client.get(export_url)
    assert response["Content-Type"] == "application/zip"
    assert response["Content-Disposition"] == 'attachment; filename="main.capy-theme.zip"'
    assert "theme.json" in zipfile.ZipFile(io.BytesIO(response.content)).namelist()


def test_import_needs_the_import_permission(client, django_user_model, theme):
    staff(client, django_user_model, "view_theme", "add_theme", "change_theme")
    assert client.get(IMPORT).status_code == 403
    listing = client.get(reverse("admin:capy_theme_theme_changelist")).content.decode()
    assert "Import theme" not in listing


def test_import_page_imports_a_draft(client, django_user_model, theme):
    data = export_theme(theme)
    staff(client, django_user_model, "view_theme", "change_theme", "import_theme")
    listing = client.get(reverse("admin:capy_theme_theme_changelist")).content.decode()
    assert f'href="{IMPORT}">Import theme</a>' in listing
    response = client.post(IMPORT, {"file": SimpleUploadedFile("main.capy-theme.zip", data)})
    imported = Theme.objects.get(name="Main (imported)")
    assert response.status_code == 302
    assert response["Location"] == reverse("admin:capy_theme_theme_change", args=[imported.pk])
    assert imported.live_revision is None


def test_import_page_shows_problems(client, django_user_model):
    staff(client, django_user_model, "view_theme", "import_theme")
    response = client.post(IMPORT, {"file": SimpleUploadedFile("x.zip", b"not a zip")})
    assert response.status_code == 200
    assert "isn&#x27;t a zip file" in response.content.decode()
    assert not Theme.objects.exists()


# Export and custom CSS (#238): the draft's custom CSS is only for edit_custom_css.

SECRET = ".draft-only { color: hotpink }"


@pytest.fixture
def secret_theme():
    return Theme.objects.create(
        name="Secret", slug="secret", settings={"custom_css": {"css": SECRET, "enabled": True}}
    )


def exported_settings(client, theme):
    response = client.get(reverse("admin:capy_theme_theme_export", args=[theme.pk]))
    assert response.status_code == 200
    manifest = json.loads(zipfile.ZipFile(io.BytesIO(response.content)).read("theme.json"))
    return manifest["theme"]["settings"]


def test_export_leaves_out_custom_css_without_the_permission(
    client, django_user_model, secret_theme
):
    staff(client, django_user_model, "view_theme", "change_theme")
    assert "custom_css" not in exported_settings(client, secret_theme)


def test_export_keeps_custom_css_with_the_permission(client, django_user_model, secret_theme):
    staff(client, django_user_model, "view_theme", "edit_custom_css")
    assert exported_settings(client, secret_theme)["custom_css"]["css"] == SECRET


def test_export_leaves_out_custom_css_when_the_project_switches_it_off(
    client, django_user_model, secret_theme, settings
):
    settings.CAPY_THEME_CUSTOM_CSS = False
    staff(client, django_user_model, "view_theme", "edit_custom_css")
    assert "custom_css" not in exported_settings(client, secret_theme)
