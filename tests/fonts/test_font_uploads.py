"""Tests for font uploads (issue #26)."""

import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from fontTools.ttLib import TTFont

from capy_theme.css.stylesheet import render_css
from capy_theme.fonts.models import Font
from capy_theme.fonts.uploads import SUBSETS, codepoints, prepare
from capy_theme.models import Theme
from capy_theme.themes.publishing import publish
from tests.support.fonts import ttf_bytes

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"


def as_woff(data, flavor):
    font = TTFont(io.BytesIO(data))
    font.flavor = flavor
    out = io.BytesIO()
    font.save(out)
    return out.getvalue()


@pytest.mark.parametrize("flavor", [None, "woff", "woff2"])
def test_ttf_woff_and_woff2_become_woff2(flavor):
    data = ttf_bytes() if flavor is None else as_woff(ttf_bytes(), flavor)
    result = prepare(data, "upload.ttf")
    assert result["file"].read()[:4] == b"wOF2"
    assert result["file"].name == "upload.woff2"


def test_weight_style_and_family_are_read_from_the_font():
    result = prepare(ttf_bytes("My Serif", weight=700, italic=True), "f.ttf")
    assert (result["weight"], result["style"], result["family"]) == (700, "italic", "My Serif")


def test_trimming_keeps_only_the_subset():
    result = prepare(ttf_bytes(), "f.ttf", "latin")
    kept = set(TTFont(io.BytesIO(result["file"].read())).getBestCmap())
    assert kept == {0x41}
    assert result["unicode_range"] == SUBSETS["latin"]


def test_not_trimming_keeps_everything():
    result = prepare(ttf_bytes(), "f.ttf", "all")
    kept = set(TTFont(io.BytesIO(result["file"].read())).getBestCmap())
    assert kept == {0x41, 0x100, 0x416}
    assert result["unicode_range"] == ""


def test_a_subset_the_font_doesnt_have_is_refused():
    with pytest.raises(ValidationError, match="no greek characters"):
        prepare(ttf_bytes(), "f.ttf", "greek")


def test_a_renamed_image_is_rejected():
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 200
    with pytest.raises(ValidationError, match="isn't a font"):
        prepare(png, "logo.ttf")


def test_too_big_is_rejected(settings):
    settings.CAPY_THEME_FONT_MAX_BYTES = 100
    with pytest.raises(ValidationError, match="too big"):
        prepare(ttf_bytes(), "f.ttf")


def test_codepoints():
    assert codepoints("U+0041, U+0100-0102") == {0x41, 0x100, 0x101, 0x102}


# Through the admin


def inline(**files):
    data = {
        "files-TOTAL_FORMS": "1",
        "files-INITIAL_FORMS": "0",
        "files-MIN_NUM_FORMS": "0",
        "files-MAX_NUM_FORMS": "1000",
        "files-0-subset": "latin",
    }
    return data | files


def test_the_issue_check_upload_a_ttf_and_it_renders(client, django_user_model):
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    upload = SimpleUploadedFile("brand.ttf", ttf_bytes("Brand Sans", weight=700), "font/ttf")
    response = client.post(
        reverse("admin:capy_theme_font_add"),
        {"family": "Brand Sans", "source": "upload"} | inline(**{"files-0-file": upload}),
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    font = Font.objects.get(family="Brand Sans")
    stored = font.files.get()
    assert stored.file.name.endswith(".woff2")
    assert stored.file.read()[:4] == b"wOF2"
    assert (stored.weight, stored.style, stored.subset) == (700, "normal", "latin")
    assert stored.unicode_range == SUBSETS["latin"]
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"body": font.pk}})
    css = render_css(publish(theme))
    assert stored.file.url in css
    assert "unicode-range: U+0000-00FF" in css


def test_the_issue_check_renamed_image_is_rejected_in_the_admin(client, django_user_model):
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    fake = SimpleUploadedFile("logo.ttf", b"\x89PNG\r\n\x1a\n" + b"\x00" * 200, "font/ttf")
    response = client.post(
        reverse("admin:capy_theme_font_add"),
        {"family": "Fake", "source": "upload"} | inline(**{"files-0-file": fake}),
    )
    assert response.status_code == 200
    assert "isn&#x27;t a font" in response.content.decode()
    assert not Font.objects.filter(family="Fake").exists()
