"""Tests for the JSON API, in its plain Django and DRF modes (issue #52)."""

import importlib

import pytest
from django.core.cache import cache
from django.core.exceptions import ImproperlyConfigured
from django.urls import clear_url_caches

from capy_theme.artifacts import api
from capy_theme.artifacts.build import get_artifacts
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
URL = "/theme/api.json"


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


@pytest.fixture
def live():
    theme = Theme.objects.create(
        name="Main", slug="main", settings={"site_name": "Capy", "shape": {"radius_box": 1}}
    )
    publish(theme)
    activate(theme)
    return theme


@pytest.mark.parametrize("which", ["drf", "django"])
def test_returns_the_artifacts(client, rf, live, mode, which):
    mode(which)
    response = client.get(URL)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("application/json")
    data = response.json()
    assert data == get_artifacts(rf.get("/"))
    assert data["branding"]["site_name"] == "Capy"
    assert data["shape"]["light"]["radius_box"] == "1rem"
    assert data["stylesheet_url"].startswith("http://testserver/theme/")
    assert response["Cache-Control"] == "public, max-age=60"


@pytest.mark.parametrize("which", ["drf", "django"])
def test_the_issue_check_etag_gives_304(client, live, mode, which):
    mode(which)
    first = client.get(URL)
    etag = first["ETag"]
    assert etag.startswith('"') and etag.endswith('"')
    second = client.get(URL, headers={"If-None-Match": etag})
    assert second.status_code == 304
    assert second["ETag"] == etag
    assert client.get(URL, headers={"If-None-Match": '"old"'}).status_code == 200


@pytest.mark.parametrize("which", ["drf", "django"])
def test_a_new_publish_changes_the_etag(client, live, mode, which):
    mode(which)
    etag = client.get(URL)["ETag"]
    live.settings = {"site_name": "New"}
    live.save()
    publish(live)
    response = client.get(URL, headers={"If-None-Match": etag})
    assert response.status_code == 200
    assert response.json()["branding"]["site_name"] == "New"


def test_both_modes_give_identical_json(client, live, mode):
    mode("drf")
    drf = client.get(URL)
    mode("django")
    plain = client.get(URL)
    assert drf.json() == plain.json()
    assert drf["ETag"] == plain["ETag"]


@pytest.mark.parametrize("which", ["drf", "django"])
def test_no_published_theme_is_404(client, mode, which):
    mode(which)
    assert client.get(URL).status_code == 404


def test_drf_mode_stays_public_whatever_the_projects_defaults(client, live, mode):
    # The test project's REST_FRAMEWORK requires login by default.
    mode("drf")
    assert client.get(URL).status_code == 200


def test_auto_uses_drf_when_installed(settings):
    settings.CAPY_THEME_API = "auto"
    assert api.api_mode() == "drf"


def test_auto_uses_django_without_drf(settings, monkeypatch):
    settings.CAPY_THEME_API = "auto"
    monkeypatch.setattr(api.apps, "is_installed", lambda name: False)
    assert api.api_mode() == "django"


def test_drf_mode_needs_drf(settings, monkeypatch):
    settings.CAPY_THEME_API = "drf"
    monkeypatch.setattr(api.apps, "is_installed", lambda name: False)
    with pytest.raises(ImproperlyConfigured, match="needs Django REST Framework"):
        api.api_mode()


def test_unknown_mode_is_an_error(settings):
    settings.CAPY_THEME_API = "graphql"
    with pytest.raises(ImproperlyConfigured, match="must be one of auto, drf, django"):
        api.api_mode()


def test_the_issue_check_listed_in_the_generated_api_docs(mode):
    from drf_spectacular.generators import SchemaGenerator

    mode("drf")
    schema = SchemaGenerator().get_schema(request=None, public=True)
    assert "/theme/api.json" in schema["paths"]
    operation = schema["paths"]["/theme/api.json"]["get"]
    assert operation["summary"] == "The active theme"
    assert "Artifacts" in schema["components"]["schemas"]
    properties = schema["components"]["schemas"]["Artifacts"]["properties"]
    assert {"colors", "fonts", "logos", "icons", "shape", "stylesheet_url"} <= set(properties)


def test_not_in_the_api_docs_in_django_mode(mode):
    from drf_spectacular.generators import SchemaGenerator

    mode("django")
    schema = SchemaGenerator().get_schema(request=None, public=True)
    assert "/theme/api.json" not in schema.get("paths", {})
