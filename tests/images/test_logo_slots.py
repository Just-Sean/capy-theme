"""Tests for logo slots: copies, choosing, fallbacks and the migration (issue #34)."""

import io

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.urls import reverse
from PIL import Image

from capy_theme.images.logos import resolve
from capy_theme.images.models import ThemeAsset, ThemeAssetVariant
from capy_theme.images.uploads import add_asset
from capy_theme.images.variants import WIDTHS
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def image(size=(600, 200), fmt="PNG", color="red", name=None):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, fmt)
    return SimpleUploadedFile(name or f"logo.{fmt.lower()}", buffer.getvalue())


def svg_logo():
    return SimpleUploadedFile(
        "logo.svg", b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 10"/>'
    )


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy"})


def choose(theme, **slots):
    """choose(theme, logo_main=asset) and publish."""
    theme.settings = {
        **theme.settings,
        "images": {slot: asset.pk for slot, asset in slots.items()},
    }
    theme.save()
    revision = publish(theme)
    activate(theme)
    return revision


def render(source):
    return Template("{% load capy_theme %}" + source).render(Context({}))


def test_header_logos_get_smaller_copies_in_three_formats(theme):
    asset = add_asset(theme, "logo_main", image((600, 200)))
    widths = sorted({v.width for v in asset.variants.all()})
    assert widths == [w for w in WIDTHS if w < 600] + [600]
    assert {v.format for v in asset.variants.all()} == {"avif", "webp", "png"}
    small = asset.variants.get(width=80, format="webp")
    assert small.height == 27  # keeps the shape: 600 × 200 → 80 × 27
    with small.file.open("rb") as f:
        assert Image.open(f).format == "WEBP"


def test_jpeg_logos_fall_back_to_jpeg(theme):
    asset = add_asset(theme, "logo_main", image(fmt="JPEG"))
    assert {v.format for v in asset.variants.all()} == {"avif", "webp", "jpeg"}


@pytest.mark.parametrize("slot", ["logo_email", "logo_print", "background_login"])
def test_other_slots_get_no_copies(theme, slot):
    asset = add_asset(theme, slot, image())
    assert not asset.variants.exists()


def test_svg_logos_get_no_copies(theme):
    asset = add_asset(theme, "logo_main", svg_logo())
    assert not asset.variants.exists()


def test_revision_has_the_chosen_images_and_their_copies(theme):
    asset = add_asset(theme, "logo_main", image())
    revision = choose(theme, logo_main=asset)
    entry = revision.snapshot["images"]["logo_main"]
    assert entry["file"] == asset.original.name
    assert (entry["width"], entry["height"]) == (600, 200)
    assert len(entry["variants"]) == ThemeAssetVariant.objects.filter(asset=asset).count()


def test_images_only_in_the_slot_they_were_uploaded_for(theme):
    asset = add_asset(theme, "logo_mark", image())
    theme.settings = {"images": {"logo_main": asset.pk}}
    with pytest.raises(Exception, match="isn't one of this theme's logo_main images"):
        theme.save()


def test_fallbacks(theme):
    main = add_asset(theme, "logo_main", image())
    mark = add_asset(theme, "logo_mark", image((100, 100)))
    snapshot = choose(theme, logo_main=main, logo_mark=mark).snapshot
    assert resolve(snapshot, "logo_main")["file"] == main.original.name
    assert resolve(snapshot, "logo_mark")["file"] == mark.original.name
    # The stacked logo has no image at all: it uses the main logo.
    assert resolve(snapshot, "logo_stacked")["file"] == main.original.name


def test_old_revisions_with_a_single_logo_still_work():
    assert resolve({"logo": "capy_theme/logos/a.png"}, "logo_mark")["file"] == (
        "capy_theme/logos/a.png"
    )
    assert resolve({"logo": ""}, "logo_main") is None


def test_admin_offers_every_slot_and_header_heights(client, django_user_model, theme):
    client.force_login(django_user_model.objects.create_superuser("sean", "s@e.com", "pw"))
    content = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content
    # A theme is a single scheme, so each logo slot has one image field (#single-scheme).
    for slot in ("main", "stacked", "mark", "wordmark", "email", "print"):
        assert f'name="image_logo_{slot}"'.encode() in content, slot
    assert b'name="logo_header_height_mobile"' in content


@pytest.mark.django_db(transaction=True)
def test_single_scheme_migration_resets_existing_themes():
    """A theme is now a single scheme, so the single-scheme migration (0019) can't
    collapse the old two-scheme data and clears every pre-existing theme instead.
    A theme created before it (and its uploaded images, moved into a logo_main asset
    by migration 0010) is gone after migrating to the latest."""
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    executor.migrate([("capy_theme", "0009_themeasset_themeassetvariant")])
    old = executor.loader.project_state([("capy_theme", "0009_themeasset_themeassetvariant")]).apps
    name = default_storage.save("capy_theme/logos/old.png", ContentFile(image().read()))
    old.get_model("capy_theme", "Theme").objects.create(
        name="Old", slug="old", logo=name, settings={"logo_alt": "Old logo"}
    )
    old.get_model("capy_theme", "Theme").objects.create(name="None", slug="none")
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())

    # The reset cascades to the pre-existing themes' revisions, assignments and images.
    assert not Theme.objects.exists()
    assert not ThemeAsset.objects.exists()
