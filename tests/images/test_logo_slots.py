"""Tests for logo slots: copies, choosing, fallbacks and the migration (issue #34)."""

import io

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.urls import reverse
from PIL import Image

from capy_theme.images.logos import resolve
from capy_theme.images.models import ThemeAssetVariant
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
    """choose(theme, logo_main={"light": asset, "dark": asset2}) and publish."""
    theme.settings = {
        **theme.settings,
        "images": {slot: {m: a.pk for m, a in modes.items()} for slot, modes in slots.items()},
    }
    theme.save()
    revision = publish(theme)
    activate(theme)
    return revision


def render(source):
    return Template("{% load capy_theme %}" + source).render(Context({}))


def test_header_logos_get_smaller_copies_in_three_formats(theme):
    asset = add_asset(theme, "logo_main", "light", image((600, 200)))
    widths = sorted({v.width for v in asset.variants.all()})
    assert widths == [w for w in WIDTHS if w < 600] + [600]
    assert {v.format for v in asset.variants.all()} == {"avif", "webp", "png"}
    small = asset.variants.get(width=80, format="webp")
    assert small.height == 27  # keeps the shape: 600 × 200 → 80 × 27
    with small.file.open("rb") as f:
        assert Image.open(f).format == "WEBP"


def test_jpeg_logos_fall_back_to_jpeg(theme):
    asset = add_asset(theme, "logo_main", "light", image(fmt="JPEG"))
    assert {v.format for v in asset.variants.all()} == {"avif", "webp", "jpeg"}


@pytest.mark.parametrize("slot", ["logo_email", "logo_print", "background_login"])
def test_other_slots_get_no_copies(theme, slot):
    asset = add_asset(theme, slot, "light", image())
    assert not asset.variants.exists()


def test_svg_logos_get_no_copies(theme):
    asset = add_asset(theme, "logo_main", "light", svg_logo())
    assert not asset.variants.exists()


def test_revision_has_the_chosen_images_and_their_copies(theme):
    asset = add_asset(theme, "logo_main", "light", image())
    revision = choose(theme, logo_main={"light": asset})
    entry = revision.snapshot["images"]["logo_main"]["light"]
    assert entry["file"] == asset.original.name
    assert (entry["width"], entry["height"]) == (600, 200)
    assert len(entry["variants"]) == ThemeAssetVariant.objects.filter(asset=asset).count()


def test_images_only_in_the_slot_they_were_uploaded_for(theme):
    asset = add_asset(theme, "logo_mark", "light", image())
    theme.settings = {"images": {"logo_main": {"light": asset.pk}}}
    with pytest.raises(Exception, match="isn't one of this theme's logo_main images"):
        theme.save()


def test_fallbacks(theme):
    main = add_asset(theme, "logo_main", "light", image())
    main_dark = add_asset(theme, "logo_main", "dark", image(color="white"))
    mark = add_asset(theme, "logo_mark", "light", image((100, 100)))
    snapshot = choose(
        theme, logo_main={"light": main, "dark": main_dark}, logo_mark={"light": mark}
    ).snapshot
    assert resolve(snapshot, "logo_main", "dark")["file"] == main_dark.original.name
    assert resolve(snapshot, "logo_mark", "light")["file"] == mark.original.name
    # The mark has no dark version: dark mode uses its light one.
    assert resolve(snapshot, "logo_mark", "dark")["file"] == mark.original.name
    # The stacked logo has no image at all: it uses the main logo.
    assert resolve(snapshot, "logo_stacked", "dark")["file"] == main_dark.original.name


def test_old_revisions_with_a_single_logo_still_work():
    assert resolve({"logo": "capy_theme/logos/a.png"}, "logo_mark", "dark")["file"] == (
        "capy_theme/logos/a.png"
    )
    assert resolve({"logo": ""}, "logo_main", "light") is None


def test_admin_offers_every_slot_and_header_heights(client, django_user_model, theme):
    client.force_login(django_user_model.objects.create_superuser("sean", "s@e.com", "pw"))
    content = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content
    for slot in ("main", "stacked", "mark", "wordmark", "email", "print"):
        for mode in ("light", "dark"):
            assert f'name="image_logo_{slot}_{mode}"'.encode() in content
    assert b'name="logo_header_height_mobile"' in content


@pytest.mark.django_db(transaction=True)
def test_migration_moves_the_old_logo_into_the_main_slot():
    from django.core.files.base import ContentFile
    from django.core.files.storage import default_storage
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    executor.migrate([("capy_theme", "0009_themeasset_themeassetvariant")])
    old = executor.loader.project_state([("capy_theme", "0009_themeasset_themeassetvariant")]).apps
    name = default_storage.save("capy_theme/logos/old.png", ContentFile(image().read()))
    theme = old.get_model("capy_theme", "Theme").objects.create(
        name="Old", slug="old", logo=name, settings={"logo_alt": "Old logo"}
    )
    old.get_model("capy_theme", "Theme").objects.create(name="None", slug="none")
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())

    moved = Theme.objects.get(pk=theme.pk)
    asset = moved.assets.get()
    assert (asset.slot, asset.mode, asset.original.name) == ("logo_main", "light", name)
    assert (asset.width, asset.height, asset.content_type) == (600, 200, "image/png")
    assert asset.alt_text == "Old logo"
    assert moved.settings["images"] == {"logo_main": {"light": asset.pk}}
    assert not Theme.objects.get(slug="none").assets.exists()
