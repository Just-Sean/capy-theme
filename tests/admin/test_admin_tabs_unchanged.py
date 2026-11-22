"""The tabs on the theme edit page are presentation only: same fields, saving and permissions."""

import io
import re
from collections import Counter
from html.parser import HTMLParser

import pytest
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from capy_theme.admin.theme_admin import ThemeAdmin
from capy_theme.images.models import ThemeAsset
from capy_theme.models import Theme

from .test_admin_tabs import panels

pytestmark = pytest.mark.django_db

STOCK_TEMPLATE = "admin/change_form.html"


class FormControls(HTMLParser):
    """What a browser would submit from the theme form, plus every id on the page."""

    def __init__(self):
        super().__init__()
        self.controls = []  # (tag, name, type)
        self.ids = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.append(attrs["id"])
        if tag in ("input", "select", "textarea") and attrs.get("name"):
            self.controls.append((tag, attrs["name"], attrs.get("type", "")))


def controls(html):
    parser = FormControls()
    parser.feed(html)
    return parser


def login(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename__in=codenames)
    )
    client.force_login(user)
    return user


def png_upload(name="logo.png"):
    buffer = io.BytesIO()
    Image.new("RGBA", (40, 20), (0, 128, 255, 255)).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


def page_with(client, url, template, monkeypatch):
    monkeypatch.setattr(ThemeAdmin, "change_form_template", template)
    return client.get(url).content.decode()


@pytest.mark.parametrize("view", ["change", "add"])
def test_the_same_form_controls_as_the_stock_admin_page(admin_client, monkeypatch, view):
    theme = Theme.objects.create(name="Main", slug="main")
    url = (
        reverse("admin:capy_theme_theme_change", args=[theme.pk])
        if view == "change"
        else reverse("admin:capy_theme_theme_add")
    )
    tabbed = controls(
        page_with(admin_client, url, "capy_theme/admin/theme_change_form.html", monkeypatch)
    )
    stock = controls(page_with(admin_client, url, STOCK_TEMPLATE, monkeypatch))
    # The buttons are capy-theme's own (Save draft, Save and publish, ...; #273), so
    # Django's save buttons and the publish note aren't compared; every field is.
    buttons = {"_save", "_continue", "_addanother", "_capy_note"}
    assert Counter(c for c in tabbed.controls if c[1] not in buttons) == Counter(
        c for c in stock.controls if c[1] not in buttons
    )


def test_no_duplicate_ids_on_the_tabbed_page(admin_client):
    theme = Theme.objects.create(name="Main", slug="main")
    html = admin_client.get(
        reverse("admin:capy_theme_theme_change", args=[theme.pk])
    ).content.decode()
    duplicates = [i for i, n in Counter(controls(html).ids).items() if n > 1]
    assert duplicates == []


def test_both_inlines_keep_their_management_forms(admin_client):
    theme = Theme.objects.create(name="Main", slug="main")
    html = admin_client.get(
        reverse("admin:capy_theme_theme_change", args=[theme.pk])
    ).content.decode()
    by_label = {label: body for _, label, body in panels(html)}
    for label in ("Media", "Revisions"):
        names = {name for _, name, _ in controls(by_label[label]).controls}
        # The prefix is whatever Django gives the inline; find it from the TOTAL_FORMS field.
        total = [n for n in names if n.endswith("-TOTAL_FORMS")]
        assert len(total) == 1, (label, names)
        stem = total[0].removesuffix("-TOTAL_FORMS")
        assert {f"{stem}-INITIAL_FORMS", f"{stem}-MIN_NUM_FORMS", f"{stem}-MAX_NUM_FORMS"} <= names


def test_the_form_is_still_multipart_for_image_uploads(admin_client):
    theme = Theme.objects.create(name="Main", slug="main")
    html = admin_client.get(
        reverse("admin:capy_theme_theme_change", args=[theme.pk])
    ).content.decode()
    assert re.search(r'<form enctype="multipart/form-data"[^>]*id="theme_form"', html)


def _post_back(html, extra=None, files=None):
    """Post the page's own fields back, the way a browser would (roughly)."""
    data = {}
    for match in re.finditer(r"<input[^>]*>", html):
        tag = match[0]
        name = re.search(r'name="([^"]+)"', tag)
        if not name or "__prefix__" in name[1]:
            continue
        kind = re.search(r'type="([^"]+)"', tag)
        kind = kind[1] if kind else "text"
        value = re.search(r'value="([^"]*)"', tag)
        if kind in ("checkbox", "radio"):
            if " checked" in tag:
                data[name[1]] = value[1] if value else "on"
        elif kind not in ("file", "submit"):
            data[name[1]] = value[1] if value else ""
    for match in re.finditer(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', html, re.S):
        if "__prefix__" in match[1]:
            continue
        chosen = re.search(r'<option value="([^"]*)"[^>]*selected', match[2])
        first = re.search(r'<option value="([^"]*)"', match[2])
        data[match[1]] = (chosen or first)[1] if (chosen or first) else ""
    for match in re.finditer(r'<textarea[^>]*name="([^"]+)"[^>]*>(.*?)</textarea>', html, re.S):
        data[match[1]] = match[2].strip()
    data.update(extra or {})
    data.update(files or {})
    return data


def test_an_image_uploaded_in_its_slot_is_saved_and_chosen(admin_client, settings, tmp_path):
    # Uploaded where it's used (Branding > Logos), not in a separate list (#271).
    settings.MEDIA_ROOT = tmp_path
    theme = Theme.objects.create(name="Main", slug="main")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    data = _post_back(admin_client.get(url).content.decode())
    data.update({"image_logo_main_upload": png_upload(), "image_logo_main_alt": "Logo"})
    response = admin_client.post(url, data)
    assert response.status_code == 302, re.findall(
        r'<ul class="errorlist[^>]*>.*?</ul>', response.content.decode(), re.S
    )
    asset = ThemeAsset.objects.get(theme=theme)
    theme.refresh_from_db()
    assert theme.settings["images"]["logo_main"] == asset.pk


def test_an_upload_error_is_inside_the_branding_tab(admin_client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    theme = Theme.objects.create(name="Main", slug="main")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    data = _post_back(admin_client.get(url).content.decode())
    data["image_logo_main_upload"] = SimpleUploadedFile("x.png", b"not an image")
    response = admin_client.post(url, data).content.decode()
    by_label = {label: body for _, label, body in panels(response)}
    assert "supported image" in by_label["Branding"]
    assert all("errorlist" not in body for label, body in by_label.items() if label != "Branding")
    assert not ThemeAsset.objects.exists()


def test_a_field_error_is_inside_its_own_tab(admin_client):
    theme = Theme.objects.create(name="Main", slug="main")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    data = _post_back(admin_client.get(url).content.decode(), {"name": ""})
    response = admin_client.post(url, data).content.decode()
    with_errors = [label for _, label, body in panels(response) if "errorlist" in body]
    assert with_errors == ["General"]


def test_a_round_trip_save_from_the_tabbed_page_succeeds(admin_client):
    theme = Theme.objects.create(name="Main", slug="main")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    data = _post_back(admin_client.get(url).content.decode(), {"name": "Renamed"})
    response = admin_client.post(url, data)
    assert response.status_code == 302
    theme.refresh_from_db()
    assert theme.name == "Renamed"


def test_no_custom_css_section_or_field_without_the_permission(client, django_user_model):
    login(client, django_user_model, "view_theme", "change_theme")
    theme = Theme.objects.create(name="Main", slug="main")
    html = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content.decode()
    labels = [label for _, label, _ in panels(html)]
    assert ">Custom CSS<" not in html
    assert "custom_css" not in {name for _, name, _ in controls(html).controls}
    assert "Advanced" in labels  # the "Advanced" section still has a home


@pytest.mark.parametrize("custom_css", [True, False])
def test_custom_css_section_with_the_permission(client, django_user_model, settings, custom_css):
    settings.CAPY_THEME_CUSTOM_CSS = custom_css
    login(client, django_user_model, "view_theme", "change_theme", "edit_custom_css")
    theme = Theme.objects.create(name="Main", slug="main")
    html = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content.decode()
    by_label = {label: body for _, label, body in panels(html)}
    assert (">Custom CSS<" in by_label["Advanced"]) is custom_css


def test_view_only_staff_see_tabs_and_cannot_save(client, django_user_model):
    login(client, django_user_model, "view_theme")
    theme = Theme.objects.create(name="Main", slug="main")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    html = client.get(url).content.decode()
    assert [label for _, label, _ in panels(html)][:2] == ["General", "Branding"]
    assert 'name="name"' not in html
    assert client.post(url, {"name": "Hacked", "slug": "main"}).status_code == 403
    theme.refresh_from_db()
    assert theme.name == "Main"


def test_no_section_lands_in_the_more_tab(admin_client, settings):
    settings.CAPY_THEME_CUSTOM_CSS = True
    theme = Theme.objects.create(name="Main", slug="main")
    html = admin_client.get(
        reverse("admin:capy_theme_theme_change", args=[theme.pk])
    ).content.decode()
    assert "More" not in [label for _, label, _ in panels(html)]


def test_the_add_page_has_no_revisions_or_stray_tabs(admin_client):
    html = admin_client.get(reverse("admin:capy_theme_theme_add")).content.decode()
    labels = [label for _, label, _ in panels(html)]
    assert "More" not in labels
    assert labels.count("General") == 1
