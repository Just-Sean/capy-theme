"""Tests for the themes catalog and per-theme assets endpoints (v2)."""

import importlib

import pytest
from django.core.cache import cache
from django.urls import clear_url_caches

from capy_theme.artifacts.build import build_artifacts, theme_catalog
from capy_theme.models import Theme
from capy_theme.themes.active import activate, catalog_theme
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
CATALOG = "/theme/themes.json"


@pytest.fixture(autouse=True)
def clear():
    cache.clear()
    yield
    cache.clear()


def reload_urls():
    import capy_theme.urls
    import tests.urls

    importlib.reload(capy_theme.urls)
    importlib.reload(tests.urls)
    clear_url_caches()


@pytest.fixture
def mode(settings):
    """mode("django") or mode("drf"): serve the API that way (reloads the URLs)."""

    def use(value):
        settings.CAPY_THEME_API = value
        reload_urls()

    yield use
    settings.CAPY_THEME_API = "auto"
    reload_urls()


def published(name, offered=False, **fields):
    theme = Theme.objects.create(
        name=name, slug=name.lower(), offered_to_visitors=offered, **fields
    )
    publish(theme)
    return theme


@pytest.fixture
def themes():
    site = published("Site")  # published + activated: the default
    activate(site)
    return {
        "site": site,
        "ocean": published("Ocean", offered=True, light_base="cupcake"),
        "forest": published("Forest", offered=True, light_base="emerald"),
        "secret": published("Secret"),  # published, but not offered and not default
    }


@pytest.mark.parametrize("which", ["drf", "django"])
def test_catalog_lists_offered_and_default_with_swatches(client, themes, mode, which):
    mode(which)
    response = client.get(CATALOG)
    assert response.status_code == 200
    data = response.json()
    entries = {e["slug"]: e for e in data}
    # Offered themes + the default (Site); "Secret" is neither.
    assert set(entries) == {"site", "ocean", "forest"}
    assert entries["site"]["default"] is True
    assert entries["ocean"]["default"] is False
    ocean = entries["ocean"]
    assert ocean["name"] == "Ocean"
    assert ocean["light"]["base"] == "cupcake"
    assert ocean["light"]["swatch"].startswith("#")
    assert ocean["dark"]["background"].startswith("#")
    assert ocean["assets_url"].endswith("/theme/themes/ocean.json")
    assert ocean["stylesheet_url"].startswith("http://testserver/theme/")
    assert response["Cache-Control"] == "public, max-age=60"
    assert "Cookie" not in response.get("Vary", "")


def test_catalog_is_empty_without_a_published_theme(client):
    response = client.get(CATALOG)
    assert response.status_code == 200
    assert response.json() == []


def test_catalog_function_matches_the_endpoint(rf, themes):
    data = theme_catalog(rf.get("/"))
    assert {e["slug"] for e in data} == {"site", "ocean", "forest"}


@pytest.mark.parametrize("which", ["drf", "django"])
def test_assets_by_slug_and_default(client, rf, themes, mode, which):
    mode(which)
    response = client.get("/theme/themes/ocean.json")
    assert response.status_code == 200
    assert response.json() == build_artifacts(themes["ocean"], rf.get("/"))
    # "default" resolves to the admin's default theme (Site).
    assert client.get("/theme/themes/default.json").json()["theme"]["slug"] == "site"
    assert catalog_theme("default") == themes["site"]


@pytest.mark.parametrize("which", ["drf", "django"])
def test_unknown_or_unoffered_theme_is_404(client, themes, mode, which):
    mode(which)
    assert client.get("/theme/themes/nope.json").status_code == 404
    # "Secret" is published but not offered and not the default — not reachable.
    assert client.get("/theme/themes/secret.json").status_code == 404


@pytest.mark.parametrize("which", ["drf", "django"])
def test_assets_etag_gives_304(client, themes, mode, which):
    mode(which)
    etag = client.get("/theme/themes/ocean.json")["ETag"]
    second = client.get("/theme/themes/ocean.json", headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second["ETag"] == etag


def test_both_modes_give_identical_json(client, themes, mode):
    mode("drf")
    drf = client.get(CATALOG).json()
    mode("django")
    plain = client.get(CATALOG).json()
    assert drf == plain
