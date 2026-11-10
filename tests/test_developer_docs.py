"""Tests that docs/developers.md matches the code (issue #57)."""

import io
import re
from pathlib import Path

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from capy_theme.css.stylesheet import render_css
from capy_theme.images.uploads import add_asset
from capy_theme.models import Font, Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
DOC = (Path(__file__).resolve().parents[1] / "docs" / "developers.md").read_text()


@pytest.fixture
def everything(settings, tmp_path):
    """A published theme with every optional feature set, so every variable appears."""
    settings.MEDIA_ROOT = tmp_path
    cache.clear()
    theme = Theme.objects.create(name="All", slug="all")
    buffer = io.BytesIO()
    Image.new("RGB", (40, 40), "red").save(buffer, "PNG")
    login = add_asset(
        theme, "background_login", "light", SimpleUploadedFile("a.png", buffer.getvalue())
    )
    pattern = add_asset(
        theme, "background_pattern", "light", SimpleUploadedFile("b.png", buffer.getvalue())
    )
    sans = Font.objects.get(family="System sans").pk
    theme.settings = {
        "fonts": dict.fromkeys(("body", "heading", "mono", "display"), sans),
        "type": {"base_size": 18, "scale": 1.25, "line_height": 1.6, "heading_weight": 700},
        "images": {
            "background_login": {"light": login.pk},
            "background_pattern": {"light": pattern.pk},
        },
    }
    theme.save()
    revision = publish(theme)
    activate(theme)
    yield revision
    cache.clear()


def documented_variables():
    return set(re.findall(r"^\| `(--[a-z0-9-]+)` \|", DOC, re.M))


def test_the_issue_check_variables_match_the_stylesheet_exactly(everything):
    defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", render_css(everything)))
    assert documented_variables() == defined


def test_the_issue_check_every_download_address_works(client, everything):
    addresses = re.findall(r"^\| `(/theme/[^`]+)` \|", DOC, re.M)
    assert addresses == ["/theme/api.json", "/theme/tokens.json", "/theme/daisyui-theme.css"]
    for address in addresses:
        assert client.get(address).status_code == 200, address
