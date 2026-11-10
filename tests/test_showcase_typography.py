"""Tests for the showcase's fonts and type section (issue #30)."""

import pytest
from django.core.cache import cache
from django.core.files.base import ContentFile

from capy_theme.active import activate
from capy_theme.models import Font, FontFile, Theme
from capy_theme.publishing import publish
from capy_theme.showcase import typography

pytestmark = pytest.mark.django_db
URL = "/theme/showcase/"


@pytest.fixture(autouse=True)
def setup(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def staff(client, django_user_model):
    client.force_login(django_user_model.objects.create_user("s", password="pw", is_staff=True))
    return client


def font_with(family, faces, subset="latin"):
    font = Font.objects.create(family=family, source="upload")
    for weight, style in faces:
        f = FontFile(font=font, weight=weight, style=style, subset=subset)
        f.file.save(f"{family}-{weight}-{style}.woff2", ContentFile(b"wOF2"), save=True)
    return font


def live(settings_values):
    theme = Theme.objects.create(name="Main", slug="main", settings=settings_values)
    revision = publish(theme)
    activate(theme)
    return theme, revision


def section(content, family):
    """The part of the page for the role card showing `family`."""
    return content.split(family, 1)[1].split("rounded-box", 1)[0]


def test_each_role_shows_its_font_and_only_real_weights():
    font = font_with("Brand Serif", [(400, "normal"), (700, "normal"), (400, "italic")])
    _, revision = live({"fonts": {"heading": font.pk}})
    roles = {r["role"]: r for r in typography(revision)["roles"]}
    assert roles["heading"]["font"]["family"] == "Brand Serif"
    assert roles["heading"]["faces"] == [
        {"weight": 400, "style": "italic"},
        {"weight": 400, "style": "normal"},
        {"weight": 700, "style": "normal"},
    ]
    assert roles["body"]["font"] is None


def test_the_issue_check_new_heading_font_changes_the_section(staff):
    first = font_with("First Serif", [(400, "normal")])
    theme, _ = live({"fonts": {"heading": first.pk}})
    assert "First Serif" in staff.get(URL).content.decode()
    second = font_with("Second Sans", [(400, "normal"), (700, "normal")])
    theme.settings = {"fonts": {"heading": second.pk}}
    theme.save()
    publish(theme)
    content = staff.get(URL).content.decode()
    assert "Second Sans" in content
    assert "First Serif" not in content


def test_the_issue_check_no_faked_bold(staff):
    regular_only = font_with("Regular Only", [(400, "normal")])
    live({"fonts": {"body": regular_only.pk}})
    card = section(staff.get(URL).content.decode(), "Regular Only")
    assert "font-weight: 400" in card
    assert "font-weight: 700" not in card


def test_type_settings_and_heading_scale_are_shown(staff):
    live({"type": {"base_size": 18, "scale": 1.25, "line_height": 1.6}})
    content = staff.get(URL).content.decode()
    assert "Heading scale (× 1.25)" in content
    assert "Base size 18px" in content
    assert "line height 1.6" in content
    assert "<h6>Heading 6 lorem ipsum</h6>" in content
    assert "<pre><code>" in content


def test_character_samples_for_the_fonts_subsets(staff):
    cyrillic = font_with("Cyr Sans", [(400, "normal")], subset="cyrillic")
    _, revision = live({"fonts": {"body": cyrillic.pk}})
    assert [name for name, _ in typography(revision)["characters"]] == ["latin", "cyrillic"]
    assert "АБВГД" in staff.get(URL).content.decode()


def test_system_fonts_note(staff):
    sans = Font.objects.get(family="System sans")
    live({"fonts": {"body": sans.pk}})
    assert "depends on the visitor" in staff.get(URL).content.decode()


def test_without_an_active_theme(staff):
    assert all(r["font"] is None for r in typography(None)["roles"])
    assert "Fonts and type" in staff.get(URL).content.decode()
