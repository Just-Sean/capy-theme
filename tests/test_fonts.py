"""Tests for the font library and font roles (issue #23)."""

import pytest
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.urls import reverse

from capy_theme.admin import ThemeForm
from capy_theme.editor import controls, preview
from capy_theme.fonts import font_css, snapshot_fonts
from capy_theme.models import Font, FontFile, Theme
from capy_theme.publishing import publish
from capy_theme.stylesheet import render_css

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


def make_font(family="Lora", weights=((400, "normal"), (700, "normal"), (400, "italic"))):
    font = Font.objects.create(family=family, source="upload", fallback_stack="Georgia, serif")
    for weight, style in weights:
        f = FontFile(font=font, weight=weight, style=style)
        f.file.save(f"{family}-{weight}-{style}.woff2", ContentFile(b"wOF2 test"), save=True)
    return font


def test_font_and_files():
    font = make_font()
    assert str(font) == "Lora"
    assert font.files.count() == 3
    assert str(font.files.get(weight=400, style="normal")) == "Lora 400 normal (latin)"


def test_theme_picks_fonts_by_role_and_snapshot_copies_them():
    font = make_font()
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"heading": font.pk}})
    fonts = theme.snapshot()["fonts"]
    assert fonts["heading"]["family"] == "Lora"
    assert len(fonts["heading"]["files"]) == 3
    assert fonts["heading"]["files"][0]["url"].startswith("/media/capy_theme/fonts/")


def test_no_fonts_key_without_fonts():
    theme = Theme.objects.create(name="Main", slug="main")
    assert "fonts" not in theme.snapshot()


def test_the_issue_check_heading_font_in_the_stylesheet():
    font = make_font()
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"heading": font.pk}})
    css = render_css(publish(theme))
    assert '@font-face {\n  font-family: "Lora";' in css
    assert css.count("@font-face") == 3
    assert "font-display: swap;" in css
    assert '--capy-font-heading: "Lora", Georgia, serif;' in css
    assert ":root :is(h1, h2, h3, h4, h5, h6) { font-family: var(--capy-font-heading); }" in css
    assert "@layer base {" in css


def test_body_and_mono_set_tailwinds_variables():
    body, mono = make_font("Inter"), make_font("JetBrains Mono")
    css = "\n".join(font_css(snapshot_fonts({"fonts": {"body": body.pk, "mono": mono.pk}})))
    assert '--font-sans: "Inter", Georgia, serif;' in css
    assert '--font-mono: "JetBrains Mono", Georgia, serif;' in css
    assert ":root body { font-family: var(--capy-font-body); }" in css


def test_default_fallbacks_by_role():
    font = Font.objects.create(family="Plain", source="upload")
    css = "\n".join(font_css(snapshot_fonts({"fonts": {"mono": font.pk}})))
    assert '--font-mono: "Plain", ui-monospace' in css


def test_published_fonts_dont_change_when_the_library_does():
    font = make_font()
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"heading": font.pk}})
    revision = publish(theme)
    font.family = "Renamed"
    font.save()
    revision.refresh_from_db()
    assert revision.snapshot["fonts"]["heading"]["family"] == "Lora"
    assert '"Lora"' in render_css(revision)


def test_unknown_font_cant_be_saved():
    with pytest.raises(ValidationError, match="isn't in the font library"):
        Theme.objects.create(name="Main", slug="main", settings={"fonts": {"body": 999}})


def test_bad_role_is_rejected_by_the_schema():
    font = make_font()
    with pytest.raises(ValidationError):
        Theme.objects.create(name="Main", slug="main", settings={"fonts": {"footer": font.pk}})


def form_data(**kwargs):
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
    }
    return data | kwargs


def test_admin_form_picks_fonts_for_roles():
    font = make_font()
    form = ThemeForm(data=form_data(font_heading=str(font.pk)))
    assert form.is_valid(), form.errors
    theme = form.save()
    assert theme.settings == {"fonts": {"heading": font.pk}}
    assert ThemeForm(instance=theme).fields["font_heading"].initial == str(font.pk)
    assert ("", "Default") in ThemeForm().fields["font_body"].choices


def test_font_admin_pages(client, django_user_model):
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    make_font()
    assert client.get(reverse("admin:capy_theme_font_changelist")).status_code == 200
    assert client.get(reverse("admin:capy_theme_font_add")).status_code == 200


def test_editor_offers_fonts_and_previews_them():
    font = make_font()
    spec = controls()
    assert [r["name"] for r in spec["font_roles"]] == ["body", "heading", "mono", "display"]
    lora = next(f for f in spec["fonts"] if f["id"] == font.pk)
    assert lora == {
        "id": font.pk,
        "family": "Lora",
        "source": "Uploaded",
        "stack": '"Lora", Georgia, serif',
    }
    theme = Theme.objects.create(name="Main", slug="main")
    result = preview(theme, {"settings": {"fonts": {"heading": font.pk}}})
    assert '--capy-font-heading: "Lora"' in result["css"]


def test_editor_refuses_unknown_fonts():
    theme = Theme.objects.create(name="Main", slug="main")
    with pytest.raises(ValidationError):
        preview(theme, {"settings": {"fonts": {"heading": 999}}})


def test_editor_state_lists_fonts(client, django_user_model):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename="change_theme")
    )
    client.force_login(user)
    make_font()
    theme = Theme.objects.create(name="Main", slug="main")
    data = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert "Lora" in [f["family"] for f in data["controls"]["fonts"]]
