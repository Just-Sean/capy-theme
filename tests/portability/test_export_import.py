"""Tests for exporting a theme and importing it on another site (issue #54)."""

import io
import json
import re
import zipfile

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from capy_theme.css.stylesheet import render_css
from capy_theme.images.uploads import add_asset
from capy_theme.models import Font, FontFile, Theme, ThemeAsset
from capy_theme.portability.export import export_theme
from capy_theme.portability.importing import import_theme
from capy_theme.themes.publishing import publish
from tests.support.fonts import ttf_bytes

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield tmp_path
    cache.clear()


def png(size=(300, 100), colour="red", name="logo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue())


@pytest.fixture
def theme():
    uploaded = Font.objects.create(
        family="Brand Sans", source="upload", fallback_stack="sans-serif"
    )
    font_file = FontFile(font=uploaded, weight=400, style="normal", subset="latin")
    from capy_theme.fonts.uploads import prepare

    checked = prepare(ttf_bytes(), "brand.ttf")
    font_file.file.save(checked["file"].name, checked["file"], save=True)
    theme = Theme.objects.create(name="Main", slug="main", light_base="cupcake")
    light = add_asset(theme, "logo_main", "light", png(), "Our logo")
    dark = add_asset(theme, "logo_main", "dark", png(colour="white", name="dark.png"))
    icon = add_asset(theme, "icon", "light", png((256, 256), name="icon.png"))
    theme.settings = {
        "site_name": "Capy",
        "colors": {"light": {"primary": "oklch(65% 0.24 350)"}},
        "shape": {"radius_box": 1},
        "fonts": {
            "body": uploaded.pk,
            "heading": Font.objects.get(family="System serif").pk,
        },
        "type": {"base_size": 18},
        "images": {
            "logo_main": {"light": light.pk, "dark": dark.pk},
            "icon": {"light": icon.pk},
        },
    }
    theme.save()
    return theme


def without_urls(css):
    return re.sub(r"/media/[^\"') ]+", "URL", css)


def test_the_issue_check_same_look_after_a_reset_and_import(theme):
    original_css = without_urls(render_css(publish(theme)).replace("Main", "THEME"))
    data = export_theme(theme)
    # "Reset the database": the theme, its images and the uploaded font are gone.
    Theme.objects.all().delete()
    Font.objects.filter(source="upload").delete()
    assert not ThemeAsset.objects.exists()

    imported = import_theme(io.BytesIO(data))
    assert imported.name == "Main" and imported.slug == "main"
    assert imported.live_revision is None  # arrives as a draft
    revision = publish(imported)
    assert without_urls(render_css(revision).replace("Main", "THEME")) == original_css
    # The images went through the upload checks again (copies remade) and the font is back.
    main = imported.assets.get(slot="logo_main", mode="light")
    assert main.alt_text == "Our logo" and main.variants.exists()
    assert Font.objects.get(family="Brand Sans").files.count() == 1
    assert imported.settings["fonts"]["heading"] == Font.objects.get(family="System serif").pk


def test_export_contents(theme):
    archive = zipfile.ZipFile(io.BytesIO(export_theme(theme)))
    manifest = json.loads(archive.read("theme.json"))
    assert manifest["format"] == "capy-theme-export/1"
    assert manifest["exported_by"].startswith("capy-theme ")
    assert "fonts" not in manifest["theme"]["settings"]
    assert set(manifest["theme"]["font_roles"]) == {"body", "heading"}
    assert len(manifest["images"]) == 3
    names = set(archive.namelist())
    assert {image["path"] for image in manifest["images"].values()} <= names
    brand = next(f for f in manifest["fonts"].values() if f["family"] == "Brand Sans")
    assert brand["files"][0]["path"] in names
    system = next(f for f in manifest["fonts"].values() if f["family"] == "System serif")
    assert system["files"] == []


def test_fonts_already_in_the_library_are_reused(theme):
    data = export_theme(theme)
    count = Font.objects.count()
    imported = import_theme(io.BytesIO(data))
    assert Font.objects.count() == count
    assert imported.settings["fonts"] == theme.settings["fonts"]


def test_a_name_that_exists_gets_imported_added(theme):
    data = export_theme(theme)
    first = import_theme(io.BytesIO(data))
    second = import_theme(io.BytesIO(data))
    assert (first.name, first.slug) == ("Main (imported)", "main-imported")
    assert (second.name, second.slug) == ("Main (imported 2)", "main-imported-2")


def zip_with(manifest, files=None):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("theme.json", json.dumps(manifest))
        for name, content in (files or {}).items():
            archive.writestr(name, content)
    buffer.seek(0)
    return buffer


def minimal(**theme):
    return {
        "format": "capy-theme-export/1",
        "theme": {
            "name": "T",
            "slug": "t",
            "light_base": "light",
            "dark_base": "dark",
            "settings": {},
        }
        | theme,
        "fonts": {},
        "images": {},
    }


@pytest.mark.parametrize(
    "upload, message",
    [
        (io.BytesIO(b"not a zip"), "isn't a zip file"),
        (zip_with({"format": "something-else"}), "isn't a capy-theme export"),
        (zip_with(minimal(light_base="no-such-theme")), "no-such-theme"),
        (zip_with(minimal(settings={"colors": {"sepia": {}}})), "sepia"),
        (zip_with(minimal(font_roles={"body": "font-9"})), "font-9"),
    ],
)
def test_bad_exports_are_rejected_and_nothing_is_kept(upload, message, media):
    with pytest.raises(ValidationError, match=message):
        import_theme(upload)
    assert not Theme.objects.exists()


def test_paths_outside_the_zip_folders_are_rejected():
    manifest = minimal()
    manifest["images"] = {"image-1": {"slot": "logo_main", "mode": "light", "path": "../x.png"}}
    with pytest.raises(ValidationError, match="isn't a capy-theme export"):
        import_theme(zip_with(manifest))


def test_a_bad_image_removes_everything_stored_so_far(media):
    manifest = minimal(image_slots={"logo_main": {"light": "image-1", "dark": "image-2"}})
    good = png().read()
    manifest["images"] = {
        "image-1": {"slot": "logo_main", "mode": "light", "path": "images/1.png"},
        "image-2": {"slot": "logo_main", "mode": "dark", "path": "images/2.png"},
    }
    upload = zip_with(manifest, {"images/1.png": good, "images/2.png": b"not an image"})
    with pytest.raises(ValidationError, match="supported image"):
        import_theme(upload)
    assert not Theme.objects.exists() and not ThemeAsset.objects.exists()
    assert not [p for p in media.rglob("*") if p.is_file()]


def test_too_big_is_rejected(settings):
    settings.CAPY_THEME_IMPORT_MAX_BYTES = 10
    with pytest.raises(ValidationError, match="too big"):
        import_theme(zip_with(minimal()))
