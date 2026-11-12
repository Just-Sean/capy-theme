"""Tests for the design tokens download (issue #53)."""

import json
from pathlib import Path

import pytest
from django.core.cache import cache
from jsonschema import Draft7Validator

from capy_theme.artifacts.tokens import build_tokens
from capy_theme.models import Font, Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
URL = "/theme/tokens.json"
SCHEMA = json.loads((Path(__file__).parent / "dtcg" / "format-2025.10.json").read_text())


@pytest.fixture(autouse=True)
def clear():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def live():
    theme = Theme.objects.create(
        name="Main",
        slug="main",
        settings={
            "colors": {"light": {"primary": "oklch(65% 0.24 350 / 0.8)"}},
            "shape": {"radius_box": 1, "noise": True},
            "fonts": {"body": Font.objects.get(family="System serif").pk},
            "type": {"base_size": 18, "scale": 1.25, "line_height": 1.6, "heading_weight": 700},
        },
    )
    publish(theme)
    activate(theme)
    return theme


def errors(document):
    return sorted(e.message for e in Draft7Validator(SCHEMA).iter_errors(document))


def test_the_issue_check_validates_against_the_format_schema(client, live):
    response = client.get(URL)
    assert response.status_code == 200
    assert errors(json.loads(response.content)) == []


def test_the_schema_does_catch_mistakes():
    # A bad color space and a dimension without a unit must fail, so the check above
    # really checks something.
    broken = {
        "a": {"$type": "color", "$value": {"colorSpace": "cmyk", "components": [0, 0, 0]}},
        "b": {"$type": "dimension", "$value": {"value": 4}},
    }
    assert errors(broken)


def test_download_headers(client, live):
    response = client.get(URL)
    assert response["Content-Type"] == "application/design-tokens+json"
    assert response["Content-Disposition"] == 'attachment; filename="main.tokens.json"'


def test_values(client, live):
    tokens = json.loads(client.get(URL).content)
    primary = tokens["light"]["color"]["primary"]
    assert primary["$type"] == "color"
    assert primary["$value"]["colorSpace"] == "oklch"
    assert primary["$value"]["components"] == [0.65, 0.24, 350]
    assert primary["$value"]["alpha"] == 0.8
    assert primary["$value"]["hex"].startswith("#") and len(primary["$value"]["hex"]) == 7
    assert len(tokens["light"]["color"]) == len(tokens["dark"]["color"]) == 20
    assert tokens["light"]["shape"]["radius-box"] == {
        "$type": "dimension",
        "$value": {"value": 1, "unit": "rem"},
    }
    assert tokens["light"]["shape"]["noise"] == {"$type": "number", "$value": 1}
    assert tokens["font"]["body"]["$type"] == "fontFamily"
    assert tokens["font"]["body"]["$value"][0] == "ui-serif"
    assert tokens["type"]["base-size"]["$value"] == {"value": 18, "unit": "px"}
    assert tokens["type"]["heading-weight"] == {"$type": "fontWeight", "$value": 700}


def test_gray_colors_have_no_hue():
    artifacts = {
        "theme": {"name": "T", "revision": 1},
        "colors": {m: {"base-100": "oklch(100% 0 0)"} for m in ("light", "dark")},
        "colors_hex": {m: {"base-100": "#ffffff"} for m in ("light", "dark")},
        "shape": {"light": {}, "dark": {}},
        "fonts": {},
        "type": {},
    }
    value = build_tokens(artifacts)["light"]["color"]["base-100"]["$value"]
    assert value["components"][2] == "none"
    assert errors(build_tokens(artifacts)) == []


def test_no_published_theme_is_404(client):
    assert client.get(URL).status_code == 404
