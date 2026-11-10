"""Tests for the management commands (issue #56)."""

import io
import shutil

import pytest
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from PIL import Image

from capy_theme.images.icons import icon_folder
from capy_theme.images.uploads import add_asset
from capy_theme.models import Font, Theme, ThemeAsset, ThemeAssetVariant
from capy_theme.themes.active import get_active_theme
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield tmp_path
    cache.clear()


def png(size=(300, 100), name="logo.png"):
    buffer = io.BytesIO()
    Image.new("RGB", size, "red").save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue())


@pytest.fixture
def theme():
    theme = Theme.objects.create(name="Main", slug="main", light_base="cupcake")
    logo = add_asset(theme, "logo_main", "light", png())
    icon = add_asset(theme, "icon", "light", png((256, 256), "icon.png"))
    theme.settings = {
        "site_name": "Capy",
        "fonts": {"body": Font.objects.get(family="System sans").pk},
        "images": {"logo_main": {"light": logo.pk}, "icon": {"light": icon.pk}},
    }
    theme.save()
    return theme


def run(*args):
    out = io.StringIO()
    call_command(*args, stdout=out)
    return out.getvalue()


def test_the_issue_check_a_fresh_install_themed_from_the_command_line(theme, media):
    path = media / "main.zip"
    assert "Exported “Main”" in run("theme_export", "main", "--output", str(path))
    # A fresh install: no themes or images.
    Theme.objects.all().delete()
    assert get_active_theme() is None
    output = run("theme_import", str(path), "--activate")
    assert "Imported “Main” (slug main) as a draft." in output
    assert "Published revision 1." in output and "is now the site's theme" in output
    active = get_active_theme()
    assert active.slug == "main" and active.live_revision.number == 1
    assert active.assets.count() == 2


def test_export_default_file_name(theme, media, monkeypatch):
    monkeypatch.chdir(media)
    run("theme_export", "main")
    assert (media / "main.capy-theme.zip").exists()


def test_import_publish_without_activating(theme, media):
    path = media / "main.zip"
    run("theme_export", "main", "-o", str(path))
    output = run("theme_import", str(path), "--publish")
    imported = Theme.objects.get(slug="main-imported")
    assert imported.live_revision is not None
    assert "is now the site's theme" not in output
    assert get_active_theme() is None


def test_import_reports_problems(media):
    bad = media / "bad.zip"
    bad.write_bytes(b"not a zip")
    with pytest.raises(CommandError, match="Not imported: That isn't a zip file."):
        run("theme_import", str(bad))
    with pytest.raises(CommandError, match="Can't read"):
        run("theme_import", str(media / "missing.zip"))


def test_publish_and_activate(theme):
    output = run("theme_publish", "main", "--note", "First", "--activate")
    assert "Published “Main” as revision 1." in output
    assert get_active_theme() == theme
    assert theme.revisions.get().note == "First"
    assert "Nothing to publish" in run("theme_publish", "main")


def test_unknown_slugs(theme):
    for command in ("theme_export", "theme_publish", "theme_rebuild_images"):
        with pytest.raises(CommandError, match="No theme with the slug 'nope'"):
            run(command, "nope")


def test_rebuild_images_remakes_copies_and_icons(theme):
    revision = publish(theme)
    folder = icon_folder(revision.snapshot)
    logo = ThemeAsset.objects.get(slot="logo_main")
    count = logo.variants.count()
    ThemeAssetVariant.objects.all().delete()  # e.g. a logo moved in by migration 0010
    shutil.rmtree(default_storage.path(folder))
    output = run("theme_rebuild_images")
    assert "Remade the copies of 2 images" in output
    assert logo.variants.count() == count
    assert default_storage.exists(f"{folder}/favicon.ico")
