"""Tests for logo slots and responsive images (issue #34)."""

import io
import re

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template, TemplateSyntaxError
from django.urls import reverse
from PIL import Image

from capy_theme.active import activate
from capy_theme.images import add_asset
from capy_theme.logos import WIDTHS, resolve
from capy_theme.models import Theme, ThemeAssetVariant
from capy_theme.publishing import publish
from capy_theme.stylesheet import render_css

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def image(size=(600, 200), fmt="PNG", colour="red", name=None):
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, fmt)
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


# Smaller copies


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


@pytest.mark.parametrize("slot", ["logo_email", "logo_print", "social"])
def test_other_slots_get_no_copies(theme, slot):
    asset = add_asset(theme, slot, "light", image())
    assert not asset.variants.exists()


def test_svg_logos_get_no_copies(theme):
    asset = add_asset(theme, "logo_main", "light", svg_logo())
    assert not asset.variants.exists()


# Choosing and publishing


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
    main_dark = add_asset(theme, "logo_main", "dark", image(colour="white"))
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


# {% theme_logo %}


def test_the_issue_check_phones_get_a_smaller_file(theme):
    asset = add_asset(theme, "logo_main", "light", image((1200, 300)))
    revision = choose(theme, logo_main={"light": asset})
    html = render("{% theme_logo %}")
    assert html.startswith("<picture>")
    assert '<source type="image/avif"' in html and '<source type="image/webp"' in html
    # 32 px high on phones (128 px wide at 4:1), 40 px elsewhere (160 px wide):
    # the browser picks the smallest copy at least that wide (× its pixel density).
    assert 'sizes="(max-width: 640px) 128px, 160px"' in html
    srcset = re.search(r'type="image/webp" srcset="([^"]+)"', html).group(1)
    assert " 128w" in srcset and " 160w" in srcset and " 1200w" in srcset
    assert f'src="/media/{asset.original.name}"' in html
    assert 'class="capy-logo"' in html
    assert 'alt="Capy"' in html
    assert 'height="300"' in html and 'width="1200"' in html
    css = render_css(revision)
    assert "img.capy-logo { height: 40px; width: auto; }" in css
    assert "@media (max-width: 640px)" in css


def test_header_heights_change_sizes_and_css(theme):
    asset = add_asset(theme, "logo_main", "light", image((400, 100)))
    theme.settings = {"logo": {"header_height": 60, "header_height_mobile": 24}}
    revision = choose(theme, logo_main={"light": asset})
    assert 'sizes="(max-width: 640px) 96px, 240px"' in render("{% theme_logo %}")
    assert "img.capy-logo { height: 60px" in render_css(revision)
    assert "img.capy-logo { height: 24px; }" in render_css(revision)


def test_the_issue_check_dark_mode_swaps_the_logo(theme):
    light = add_asset(theme, "logo_main", "light", image(), "Light logo")
    dark = add_asset(theme, "logo_main", "dark", image(colour="white"), "Dark logo")
    revision = choose(theme, logo_main={"light": light, "dark": dark})
    html = render("{% theme_logo %}")
    assert html.count("<picture") == 2
    first, second = html.split("</picture>")[:2]
    assert 'class="capy-logo-light"' in first and light.original.name in first
    assert 'class="capy-logo-dark"' in second and dark.original.name in second
    # Lazy, so the hidden one isn't downloaded until the mode changes.
    assert html.count('loading="lazy"') == 2
    css = render_css(revision)
    assert ':root[data-theme="capy-dark"] .capy-logo-light { display: none; }' in css
    assert ":root:not([data-theme]) .capy-logo-dark { display: inline; }" in css


def test_alt_text_from_the_image_then_the_theme_then_the_site_name(theme):
    asset = add_asset(theme, "logo_main", "light", image(), "Capy & friends")
    choose(theme, logo_main={"light": asset})
    assert 'alt="Capy &amp; friends"' in render("{% theme_logo %}")


def test_slot_argument(theme):
    main = add_asset(theme, "logo_main", "light", image())
    mark = add_asset(theme, "logo_mark", "light", svg_logo())
    choose(theme, logo_main={"light": main}, logo_mark={"light": mark})
    html = render('{% theme_logo slot="mark" class="h-6" %}')
    assert html == (
        f'<img src="/media/{mark.original.name}" alt="Capy" class="capy-logo h-6" '
        'height="10" width="30">'
    )
    assert main.original.name in render('{% theme_logo slot="stacked" %}')  # fallback
    email = render('{% theme_logo slot="email" %}')
    assert "capy-logo" not in email and "srcset" not in email  # not a header logo


def test_unknown_slot_is_an_error(theme):
    choose(theme)
    with pytest.raises(TemplateSyntaxError, match="unknown slot"):
        render('{% theme_logo slot="footer" %}')


# The live editor


@pytest.fixture
def editor_client(client, django_user_model):
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    return client


def test_editor_saves_logo_choices_and_heights(editor_client, theme):
    asset = add_asset(theme, "logo_main", "dark", image())
    state = editor_client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert [s["name"] for s in state["controls"]["logo_slots"]][0] == "logo_main"
    assert {h["name"] for h in state["controls"]["logo_heights"]} == {
        "header_height",
        "header_height_mobile",
    }
    changes = {
        "settings": {
            "images": {"logo_main": {"dark": asset.pk}},
            "logo": {"header_height": 48},
        }
    }
    url = reverse("capy_theme:editor_preview", args=[theme.pk])
    preview = editor_client.post(url, changes, content_type="application/json").json()
    assert "img.capy-logo { height: 48px" in preview["css"]
    url = reverse("capy_theme:editor_save", args=[theme.pk])
    assert editor_client.post(url, changes, content_type="application/json").status_code == 200
    theme.refresh_from_db()
    assert theme.settings["images"] == {"logo_main": {"dark": asset.pk}}
    assert theme.settings["logo"] == {"header_height": 48}


def test_editor_rejects_another_themes_image(editor_client, theme):
    other = Theme.objects.create(name="Other", slug="other")
    asset = add_asset(other, "logo_main", "light", image())
    url = reverse("capy_theme:editor_preview", args=[theme.pk])
    changes = {"settings": {"images": {"logo_main": {"light": asset.pk}}}}
    response = editor_client.post(url, changes, content_type="application/json")
    assert response.status_code == 400
    assert "isn't one of this theme's" in response.json()["errors"][0]


# Moving the old single logo into the main slot (migration 0010)


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
