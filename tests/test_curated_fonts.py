"""Tests for the curated font collection (issue #25)."""

import json
from io import StringIO
from pathlib import Path

import pytest
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.urls import reverse

from capy_theme.models import Font

pytestmark = pytest.mark.django_db
MODULE = Path(__file__).resolve().parent.parent / "src" / "capy_theme"
MANIFEST = json.loads((MODULE / "curated_fonts.json").read_text())
FONTS = MODULE / "static" / "capy_theme" / "fonts"


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


def test_about_30_open_licence_fonts_are_bundled():
    assert len(MANIFEST) == 30
    assert {f["category"] for f in MANIFEST} == {"sans", "serif", "mono", "display"}
    for font in MANIFEST:
        assert font["licence"] == "SIL Open Font License 1.1"
        assert (FONTS / font["id"] / "LICENSE").exists(), font["id"]
        assert font["files"], font["id"]
        for item in font["files"]:
            assert (FONTS / item["path"]).read_bytes()[:4] == b"wOF2", item["path"]


def test_the_command_adds_them_to_the_library():
    out = StringIO()
    call_command("capy_theme_add_fonts", stdout=out)
    assert "Done: 30 fonts added, 0 already in the library." in out.getvalue()
    inter = Font.objects.get(family="Inter")
    assert inter.source == "bundled"
    assert "SIL Open Font License 1.1" in inter.licence
    assert {(f.weight, f.style) for f in inter.files.all()} == {
        (400, "normal"),
        (700, "normal"),
        (400, "italic"),
    }
    assert default_storage.exists(inter.files.first().file.name)


def test_running_it_again_skips_existing_fonts():
    call_command("capy_theme_add_fonts", stdout=StringIO())
    out = StringIO()
    call_command("capy_theme_add_fonts", stdout=out)
    assert "Done: 0 fonts added, 30 already in the library." in out.getvalue()
    assert Font.objects.filter(source="bundled").count() == 30


def test_the_font_list_has_a_preview_of_each(client, django_user_model):
    call_command("capy_theme_add_fonts", stdout=StringIO())
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    content = client.get(reverse("admin:capy_theme_font_changelist") + "?all=").content.decode()
    assert content.count("The quick brown fox jumps over the lazy dog") >= 30
    assert '@font-face{font-family:"Inter"' in content
    assert "font-family: &quot;Inter&quot;, ui-sans-serif" in content


def test_editor_samples_use_each_fonts_stack():
    from capy_theme.editor import controls

    call_command("capy_theme_add_fonts", stdout=StringIO())
    lora = next(f for f in controls()["fonts"] if f["family"] == "Lora")
    assert lora["stack"].startswith('"Lora", ui-serif')
