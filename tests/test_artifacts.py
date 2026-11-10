"""Tests for theme artifacts: what other modules get from capy-theme (issue #143)."""

import io

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from PIL import Image

from capy_theme.active import activate
from capy_theme.artifacts import get_artifacts
from capy_theme.builtin_themes import THEMES
from capy_theme.colors import to_hex
from capy_theme.icons import FILES
from capy_theme.images import add_asset
from capy_theme.models import Font, Theme
from capy_theme.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.MEDIA_URL = "/media/"
    cache.clear()
    yield
    cache.clear()


def png(size=(400, 100), colour="red", name="img.png"):
    buffer = io.BytesIO()
    Image.new("RGB", size, colour).save(buffer, "PNG")
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
        "main": add_asset(theme, "logo_main", "light", png(name="main.png")),
        "main_dark": add_asset(theme, "logo_main", "dark", png(colour="blue", name="dark.png")),
        "email": add_asset(theme, "logo_email", "light", png(name="email.png"), "Email logo"),
        "icon": add_asset(theme, "icon", "light", png((256, 256), name="icon.png")),
        "social": add_asset(theme, "social", "light", png((1300, 700), name="share.png"), "Shop"),
        "pattern": add_asset(theme, "background_pattern", "light", png((16, 16), name="p.png")),
    }
    theme.settings = {
        **theme.settings,
        "fonts": {"body": Font.objects.get(family="System sans").pk},
        "images": {
            "logo_main": {"light": assets["main"].pk, "dark": assets["main_dark"].pk},
            "logo_email": {"light": assets["email"].pk},
            "icon": {"light": assets["icon"].pk},
            "social": {"light": assets["social"].pk},
            "background_pattern": {"light": assets["pattern"].pk},
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
    assert artifacts["theme"] == {"name": "Main", "slug": "main", "revision": 1}
    assert artifacts["branding"] == {
        "site_name": "Capy",
        "tagline": "Hello",
        "logo_alt": "Capy logo",
    }
    # Colours: all 20, per mode, as OKLCH and as hex for emails.
    assert len(artifacts["colors"]["light"]) == 20
    primary = THEMES["light"]["values"]["--color-primary"]
    assert artifacts["colors"]["light"]["primary"] == primary
    assert artifacts["colors_hex"]["light"]["primary"] == to_hex(primary, alpha=False)
    assert artifacts["colors_hex"]["dark"]["base-100"].startswith("#")
    # Fonts.
    assert artifacts["fonts"]["body"]["family"] == "System sans"
    assert artifacts["fonts"]["body"]["source"] == "system"
    # Logos, after fallbacks.
    logos = artifacts["logos"]
    main = logos["logo_main"]["light"]
    assert main["url"] == f"/media/{assets['main'].original.name}"
    assert main["alt"] == "Capy logo"
    assert {v["format"] for v in main["variants"]} == {"avif", "webp", "png"}
    assert logos["logo_main"]["dark"]["url"] == f"/media/{assets['main_dark'].original.name}"
    assert logos["logo_mark"]["dark"]["url"] == logos["logo_main"]["dark"]["url"]  # fallback
    assert logos["logo_email"]["light"]["alt"] == "Email logo"
    assert logos["logo_email"]["dark"]["url"] == f"/media/{assets['email'].original.name}"
    assert logos["logo_email"]["light"]["variants"] == []
    # Icons: every generated file, including those a manifest needs.
    assert set(artifacts["icons"]) == set(FILES)
    assert artifacts["icons"]["icon-maskable-512.png"].startswith("/media/capy_theme/icons/")
    # Sharing image and backgrounds.
    sharing = artifacts["sharing_image"]
    assert (sharing["width"], sharing["height"], sharing["alt"]) == (1200, 630, "Shop")
    assert sharing["url"].endswith("-1200x630.png")
    assert artifacts["backgrounds"]["pattern"]["dark"] == (
        f"/media/{assets['pattern'].original.name}"
    )
    assert artifacts["backgrounds"]["login"] == {"light": None, "dark": None}
    assert artifacts["mode"] == {"default": "auto", "visitors_can_switch": True}
    assert artifacts["stylesheet_url"].startswith("/theme/")


def test_urls_are_absolute_with_a_request(published, rf):
    artifacts = get_artifacts(rf.get("/"))
    assert artifacts["logos"]["logo_email"]["light"]["url"].startswith("http://testserver/media/")
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
    assert artifacts["logos"]["logo_main"] == {"light": None, "dark": None}
    assert artifacts["icons"] == {}
    assert artifacts["sharing_image"] is None
    assert artifacts["fonts"] == {}


def test_template_tag(published, rf):
    _, assets = published
    html = Template(
        "{% load capy_theme %}{% theme_artifacts as a %}"
        "{{ a.logos.logo_email.light.url }}|{{ a.colors_hex.light.primary }}|"
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

    executor = MigrationExecutor(connection)
    executor.migrate([("capy_theme", "0010_logo_slots")])
    old = executor.loader.project_state([("capy_theme", "0010_logo_slots")]).apps
    theme = old.get_model("capy_theme", "Theme").objects.create(
        name="Old",
        slug="old",
        settings={"site_name": "Capy", "app": {"name": "X"}, "social": {"description": "Y"}},
    )
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(executor.loader.graph.leaf_nodes())
    migrated = Theme.objects.get(pk=theme.pk)
    assert migrated.settings == {"site_name": "Capy"}
    migrated.save()  # valid again under the new schema
