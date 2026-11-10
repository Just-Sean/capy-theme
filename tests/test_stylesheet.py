"""Tests for the theme stylesheet (issue #8)."""

import importlib
import importlib.metadata

import pytest
from django.urls import reverse

from capy_theme.builtin_themes import THEMES
from capy_theme.models import Theme
from capy_theme.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main", light_base="cupcake", dark_base="dracula")


def css_url(revision):
    return reverse("capy_theme:theme_css", args=[revision.css_version])


def test_stylesheet_url_is_under_theme(theme):
    revision = publish(theme)
    assert css_url(revision) == f"/theme/{revision.css_version}.css"
    assert len(revision.css_version) == 12


def css_blocks(css):
    """Return {selector: block text} for the stylesheet's four rule blocks."""
    blocks = {}
    for selector in (
        ":root {",
        "@media (prefers-color-scheme: dark)",
        '[data-theme="capy-light"]',
        '[data-theme="capy-dark"]',
    ):
        start = css.index(selector)
        blocks[selector] = css[start : css.index("}", start)]
    return blocks


def test_stylesheet_has_variables_for_both_modes(client, theme):
    revision = publish(theme)
    response = client.get(css_url(revision))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/css; charset=utf-8"
    cupcake = THEMES["cupcake"]["values"]["--color-primary"]
    dracula = THEMES["dracula"]["values"]["--color-primary"]
    expected = {
        ":root {": ("light", cupcake),
        "@media (prefers-color-scheme: dark)": ("dark", dracula),
        '[data-theme="capy-light"]': ("light", cupcake),
        '[data-theme="capy-dark"]': ("dark", dracula),
    }
    for selector, block in css_blocks(response.content.decode()).items():
        scheme, primary = expected[selector]
        assert f"color-scheme: {scheme};" in block, selector
        assert f"--color-primary: {primary};" in block, selector
        assert block.count("--") == 28, selector  # all 28 values


def test_stylesheet_is_cached_by_browsers_for_a_year(client, theme):
    response = client.get(css_url(publish(theme)))
    assert response["Cache-Control"] == "public, max-age=31536000, immutable"


def test_publishing_changes_the_url_and_the_old_url_still_works(client, theme):
    first = publish(theme)
    theme.light_base = "emerald"
    theme.save()
    second = publish(theme)
    assert first.css_version != second.css_version

    old = client.get(css_url(first)).content.decode()
    new = client.get(css_url(second)).content.decode()
    assert THEMES["cupcake"]["values"]["--color-primary"] in old
    assert THEMES["emerald"]["values"]["--color-primary"] in new


def test_unknown_version_is_not_found(client):
    assert client.get("/theme/000000000000.css").status_code == 404


def test_stylesheet_uses_the_saved_values_not_todays_daisyui(client, theme, monkeypatch):
    revision = publish(theme)
    # Simulate a daisyUI update changing cupcake after the theme was published.
    changed = dict(THEMES["cupcake"]["values"], **{"--color-primary": "oklch(1% 0 0)"})
    monkeypatch.setitem(THEMES, "cupcake", {"scheme": "light", "values": changed})
    css = client.get(css_url(revision)).content.decode()
    assert "oklch(1% 0 0)" not in css
    assert revision.snapshot["light_values"]["--color-primary"] in css


def test_stylesheet_survives_a_removed_daisyui_theme(client, theme, monkeypatch):
    revision = publish(theme)
    monkeypatch.delitem(THEMES, "cupcake")
    assert client.get(css_url(revision)).status_code == 200


def test_admin_links_to_the_live_stylesheet(client, theme, django_user_model):
    user = django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")
    client.force_login(user)
    revision = publish(theme)
    response = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk]))
    assert css_url(revision).encode() in response.content


# Migration 0004 fills in values for revisions published before it.


def test_migration_fills_in_values_for_old_revisions():
    migration = importlib.import_module(
        "capy_theme.migrations.0004_revision_values_and_css_version"
    )
    old = {"light_base": "cupcake", "dark_base": "gone", "settings": {}}
    filled = migration.fill_values(old, THEMES)
    assert filled["light_values"] == THEMES["cupcake"]["values"]
    assert filled["dark_values"] is None  # base no longer in daisyUI
    assert "light_values" not in old  # original untouched


def test_migration_version_matches_the_module():
    from capy_theme.stylesheet import css_version

    migration = importlib.import_module(
        "capy_theme.migrations.0004_revision_values_and_css_version"
    )
    snapshot = {"light_base": "light", "dark_base": "dark", "settings": {}}
    assert migration.css_version(1, 2, snapshot) == css_version(1, 2, snapshot)


# The package version in stylesheet URLs (issue #86)


def test_stylesheet_url_includes_the_package_version(theme):
    from capy_theme.stylesheet import stylesheet_url

    revision = publish(theme)
    version = importlib.metadata.version("capy-theme")
    assert stylesheet_url(revision) == f"/theme/{revision.css_version}.css?v={version}"


def test_package_version_changes_the_url(theme, monkeypatch):
    from capy_theme import stylesheet

    revision = publish(theme)
    before = stylesheet.stylesheet_url(revision)
    monkeypatch.setattr(stylesheet, "version", lambda name: "9.9.9")
    after = stylesheet.stylesheet_url(revision)
    assert before != after
    assert after.endswith("?v=9.9.9")


def test_stylesheet_is_served_with_or_without_v(client, theme):
    revision = publish(theme)
    plain = client.get(css_url(revision))
    versioned = client.get(css_url(revision) + "?v=0.1.0")
    assert plain.status_code == versioned.status_code == 200
    assert plain.content == versioned.content
