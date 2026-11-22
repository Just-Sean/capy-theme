"""Tests for theme artifacts: what other modules get from capy-theme (issue #143)."""

import io

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from PIL import Image

from capy_theme.artifacts import get_artifacts
from capy_theme.colors.color_math import to_hex
from capy_theme.fonts.models import Font
from capy_theme.images.icons import FILES
from capy_theme.images.uploads import add_asset
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.catalog import THEMES
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def png(size=(400, 100), color="red", name="img.png"):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "PNG")
    return SimpleUploadedFile(name, buffer.getvalue())


@pytest.fixture
def published():
    """A published theme with logos, an icon, a sharing image and a background."""
    theme = Theme.objects.create(
        name="Main",
        slug="main",
        settings={"site_name": "Capy", "tagline": "Hello", "logo_alt": "Capy logo"},
    )
    assets = {
        "main": add_asset(theme, "logo_main", png(name="main.png")),
        "email": add_asset(theme, "logo_email", png(name="email.png"), "Email logo"),
        "icon": add_asset(theme, "icon", png((256, 256), name="icon.png")),
        "social": add_asset(theme, "social", png((1300, 700), name="share.png"), "Shop"),
        "pattern": add_asset(theme, "background_pattern", png((16, 16), name="p.png")),
    }
    theme.settings = {
        **theme.settings,
        "fonts": {"body": Font.objects.get(family="System sans").pk},
        "images": {
            "logo_main": assets["main"].pk,
            "logo_email": assets["email"].pk,
            "icon": assets["icon"].pk,
            "social": assets["social"].pk,
            "background_pattern": assets["pattern"].pk,
        },
    }
    theme.save()
    publish(theme)
    activate(theme)
    return theme, assets


def test_none_without_a_published_theme():
    assert get_artifacts() is None


def test_the_issue_check_every_artifact_without_touching_models(published):
    theme, assets = published
    artifacts = get_artifacts()
    assert artifacts["theme"] == {
        "name": "Main",
        "slug": "main",
        "scheme": "light",
        "revision": 1,
    }
    assert artifacts["branding"] == {
        "site_name": "Capy",
        "tagline": "Hello",
        "logo_alt": "Capy logo",
    }
    # Colors: all 20, flat, as OKLCH and as hex for emails.
    assert len(artifacts["colors"]) == 20
    primary = THEMES["light"]["values"]["--color-primary"]
    assert artifacts["colors"]["primary"] == primary
    assert artifacts["colors_hex"]["primary"] == to_hex(primary, alpha=False)
    assert artifacts["colors_hex"]["base-100"].startswith("#")
    # Fonts.
    assert artifacts["fonts"]["body"]["family"] == "System sans"
    assert artifacts["fonts"]["body"]["source"] == "system"
    # Logos, after fallbacks.
    logos = artifacts["logos"]
    main = logos["logo_main"]
    assert main["url"] == f"/media/{assets['main'].original.name}"
    assert main["alt"] == "Capy logo"
    assert {v["format"] for v in main["variants"]} == {"avif", "webp", "png"}
    assert logos["logo_mark"]["url"] == logos["logo_main"]["url"]  # fallback
    assert logos["logo_email"]["alt"] == "Email logo"
    assert logos["logo_email"]["url"] == f"/media/{assets['email'].original.name}"
    assert logos["logo_email"]["variants"] == []
    # Icons: every generated file, including those a manifest needs.
    assert set(artifacts["icons"]) == set(FILES)
    assert artifacts["icons"]["icon-maskable-512.png"].startswith("/media/capy_theme/icons/")
    # Sharing image and backgrounds.
    sharing = artifacts["sharing_image"]
    assert (sharing["width"], sharing["height"], sharing["alt"]) == (1200, 630, "Shop")
    assert sharing["url"].endswith("-1200x630.png")
    assert artifacts["backgrounds"]["pattern"] == f"/media/{assets['pattern'].original.name}"
    assert artifacts["backgrounds"]["login"] is None
    assert "mode" not in artifacts
    assert artifacts["stylesheet_url"].startswith("/theme/")


def test_urls_are_absolute_with_a_request(published, rf):
    artifacts = get_artifacts(rf.get("/"))
    assert artifacts["logos"]["logo_email"]["url"].startswith("http://testserver/media/")
    assert artifacts["icons"]["icon-512.png"].startswith("http://testserver/media/")
    assert artifacts["sharing_image"]["url"].startswith("http://testserver/media/")
    assert artifacts["stylesheet_url"].startswith("http://testserver/theme/")


def test_published_values_not_the_draft(published):
    theme, _ = published
    theme.settings = {**theme.settings, "site_name": "Draft"}
    theme.save()
    assert get_artifacts()["branding"]["site_name"] == "Capy"


def test_empty_theme_has_empty_artifacts():
    theme = Theme.objects.create(name="Plain", slug="plain")
    publish(theme)
    activate(theme)
    artifacts = get_artifacts()
    assert artifacts["logos"]["logo_main"] is None
    assert artifacts["icons"] == {}
    assert artifacts["sharing_image"] is None
    assert artifacts["fonts"] == {}


def test_template_tag(published, rf):
    _, assets = published
    html = Template(
        "{% load capy_theme %}{% theme_artifacts as a %}"
        "{{ a.logos.logo_email.url }}|{{ a.colors_hex.primary }}|"
        '{{ a.icons|capy_get:"icon-512.png" }}'
    ).render(Context({"request": rf.get("/")}))
    email, primary, icon = html.split("|")
    assert email == f"http://testserver/media/{assets['email'].original.name}"
    assert primary.startswith("#")
    assert icon.startswith("http://testserver/media/capy_theme/icons/")


@pytest.mark.django_db(transaction=True)
def test_migration_removes_app_and_social_settings():
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    target = [("capy_theme", "0011_remove_app_and_social_settings")]
    executor = MigrationExecutor(connection)
    executor.migrate([("capy_theme", "0010_logo_slots")])
    old = executor.loader.project_state([("capy_theme", "0010_logo_slots")]).apps
    theme = old.get_model("capy_theme", "Theme").objects.create(
        name="Old",
        slug="old",
        settings={"site_name": "Capy", "app": {"name": "X"}, "social": {"description": "Y"}},
    )
    # Migrate only up to the migration under test: a later migration (0019)
    # clears every theme when a theme became a single scheme.
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(target)
    migrated_apps = executor.loader.project_state(target).apps
    migrated = migrated_apps.get_model("capy_theme", "Theme").objects.get(pk=theme.pk)
    assert migrated.settings == {"site_name": "Capy"}
    # Restore the full migration state for the rest of the suite.
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
