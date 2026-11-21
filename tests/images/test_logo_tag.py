"""Tests for the logo rendering (logo_html) and the editor's logo choices (issue #34).

In v2 the logo is rendered by the consumer, not a {% theme_logo %} tag; capy-theme exposes
the rendering engine (``logo_html``) and the image data (artifacts), tested here.
"""

import io
import re

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from capy_theme.css.stylesheet import render_css
from capy_theme.images.logo_tag import logo_html
from capy_theme.images.uploads import add_asset
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


def logo(revision, slot="logo_main", attrs=None):
    """Render a published logo the way the engine does (what the old tag called)."""
    return logo_html(revision.snapshot, slot, "Capy", attrs or {}, {})


def test_the_issue_check_phones_get_a_smaller_file(theme):
    asset = add_asset(theme, "logo_main", image((1200, 300)))
    revision = choose(theme, logo_main=asset)
    html = logo(revision)
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
    asset = add_asset(theme, "logo_main", image((400, 100)))
    theme.settings = {"logo": {"header_height": 60, "header_height_mobile": 24}}
    revision = choose(theme, logo_main=asset)
    assert 'sizes="(max-width: 640px) 96px, 240px"' in logo(revision)
    assert "img.capy-logo { height: 60px" in render_css(revision)
    assert "img.capy-logo { height: 24px; }" in render_css(revision)


def test_logo_renders_a_single_picture(theme):
    # A theme is a single scheme now, so its logo is one <picture>, not a
    # light/dark pair that the browser swaps by mode.
    asset = add_asset(theme, "logo_main", image(), "Our logo")
    revision = choose(theme, logo_main=asset)
    html = logo(revision)
    assert html.count("<picture") == 1
    assert asset.original.name in html
    assert "capy-logo-light" not in html and "capy-logo-dark" not in html
    assert 'loading="lazy"' not in html  # the one logo isn't lazy-loaded
    css = render_css(revision)
    # The CSS only sizes the header logo; no light/dark display switching remains.
    assert "img.capy-logo { height:" in css
    assert ".capy-logo-light" not in css and ".capy-logo-dark" not in css


def test_alt_text_from_the_image_then_the_theme_then_the_site_name(theme):
    asset = add_asset(theme, "logo_main", image(), "Capy & friends")
    revision = choose(theme, logo_main=asset)
    assert 'alt="Capy &amp; friends"' in logo(revision)


def test_slot_argument(theme):
    main = add_asset(theme, "logo_main", image())
    mark = add_asset(theme, "logo_mark", svg_logo())
    revision = choose(theme, logo_main=main, logo_mark=mark)
    html = logo(revision, "logo_mark", {"class": "h-6"})
    assert html == (
        f'<img src="/media/{mark.original.name}" alt="Capy" class="capy-logo h-6" '
        'height="10" width="30">'
    )
    assert main.original.name in logo(revision, "logo_stacked")  # fallback
    email = logo(revision, "logo_email")
    assert "capy-logo" not in email and "srcset" not in email  # not a header logo


@pytest.fixture
def editor_client(client, django_user_model):
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user("ed", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    client.force_login(user)
    return client


def test_editor_saves_logo_choices_and_heights(editor_client, theme):
    asset = add_asset(theme, "logo_main", image())
    state = editor_client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert [s["name"] for s in state["controls"]["image_slots"]][0] == "logo_main"
    assert {h["name"] for h in state["controls"]["logo_heights"]} == {
        "header_height",
        "header_height_mobile",
    }
    changes = {
        "settings": {
            "images": {"logo_main": asset.pk},
            "logo": {"header_height": 48},
        }
    }
    url = reverse("capy_theme:editor_preview", args=[theme.pk])
    preview = editor_client.post(url, changes, content_type="application/json").json()
    assert "img.capy-logo { height: 48px" in preview["css"]
    url = reverse("capy_theme:editor_save", args=[theme.pk])
    assert editor_client.post(url, changes, content_type="application/json").status_code == 200
    theme.refresh_from_db()
    assert theme.settings["images"] == {"logo_main": asset.pk}
    assert theme.settings["logo"] == {"header_height": 48}


def test_editor_rejects_another_themes_image(editor_client, theme):
    other = Theme.objects.create(name="Other", slug="other")
    asset = add_asset(other, "logo_main", image())
    url = reverse("capy_theme:editor_preview", args=[theme.pk])
    changes = {"settings": {"images": {"logo_main": asset.pk}}}
    response = editor_client.post(url, changes, content_type="application/json")
    assert response.status_code == 400
    assert "isn't one of this theme's" in response.json()["errors"][0]
