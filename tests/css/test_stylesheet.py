"""Tests for the theme stylesheet (issue #8)."""

import importlib
import importlib.metadata

import pytest
from django.urls import reverse

from capy_theme.css.stylesheet import snapshot_css
from capy_theme.models import Theme
from capy_theme.themes.catalog import THEMES
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main", base="cupcake")


def css_url(revision):
    return reverse("capy_theme:theme_css", args=[revision.css_version])


def test_stylesheet_url_is_under_theme(theme):
    revision = publish(theme)
    assert css_url(revision) == f"/theme/{revision.css_version}.css"
    assert len(revision.css_version) == 12


def block(css, selector):
    """The rule block text that starts with `selector`."""
    start = css.index(selector)
    return css[start : css.index("}", start)]


def test_light_stylesheet_has_the_light_scheme(client, theme):
    # A light theme renders only the light scheme: the default (:root) and the
    # forced light block ([data-theme="capy-light"]).
    revision = publish(theme)
    response = client.get(css_url(revision))
    assert response.status_code == 200
    assert response["Content-Type"] == "text/css; charset=utf-8"
    css = response.content.decode()
    cupcake = THEMES["cupcake"]["values"]["--color-primary"]
    assert "@media (prefers-color-scheme: dark)" not in css
    assert '[data-theme="capy-dark"]' not in css
    for selector in (":root {", '[data-theme="capy-light"]'):
        rules = block(css, selector)
        assert "color-scheme: light;" in rules, selector
        assert f"--color-primary: {cupcake};" in rules, selector
        assert rules.count("--") == 29, selector  # all 28 values, plus --capy-focus


def test_dark_stylesheet_has_the_dark_scheme(client):
    # A dark theme renders only the dark scheme: the device-dark media query and
    # the forced dark block ([data-theme="capy-dark"]).
    revision = publish(Theme.objects.create(name="Night", slug="night", base="dracula"))
    css = client.get(css_url(revision)).content.decode()
    dracula = THEMES["dracula"]["values"]["--color-primary"]
    assert "@media (prefers-color-scheme: dark) {" in css
    assert ':root:not([data-theme="capy-light"]) {' in css
    for selector in (':root:not([data-theme="capy-light"]) {', '[data-theme="capy-dark"]'):
        rules = block(css, selector)
        assert "color-scheme: dark;" in rules, selector
        assert f"--color-primary: {dracula};" in rules, selector
        assert rules.count("--") == 29, selector  # all 28 values, plus --capy-focus


def test_stylesheet_is_cached_by_browsers_for_a_year(client, theme):
    response = client.get(css_url(publish(theme)))
    assert response["Cache-Control"] == "public, max-age=31536000, immutable"


def test_publishing_changes_the_url_and_the_old_url_still_works(client, theme):
    first = publish(theme)
    theme.base = "emerald"
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
    assert revision.snapshot["values"]["--color-primary"] in css


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
    from capy_theme.css.stylesheet import css_version

    migration = importlib.import_module(
        "capy_theme.migrations.0004_revision_values_and_css_version"
    )
    snapshot = {"light_base": "light", "dark_base": "dark", "settings": {}}
    assert migration.css_version(1, 2, snapshot) == css_version(1, 2, snapshot)


# The package version in stylesheet URLs (issue #86)


def test_stylesheet_url_includes_the_package_version(theme):
    from capy_theme.css.stylesheet import stylesheet_url

    revision = publish(theme)
    version = importlib.metadata.version("capy-theme")
    assert stylesheet_url(revision) == f"/theme/{revision.css_version}.css?v={version}"


def test_package_version_changes_the_url(theme, monkeypatch):
    from capy_theme.css import stylesheet

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


# A theme name can't end the CSS comment it's written into (#253).

ESCAPE = 'x */ @import url("https://evil.example/x.css"); /*'


def test_a_name_with_a_comment_end_stays_inside_the_comment(client):
    theme = Theme.objects.create(name=ESCAPE, slug="evil")
    css = client.get(css_url(publish(theme))).content.decode()
    first_line = css.splitlines()[0]
    assert (
        first_line
        == '/* capy-theme: x * / @import url("https://evil.example/x.css"); /*, revision 1 */'
    )
    assert first_line.count("*/") == 1 and first_line.endswith("*/")


def test_editor_css_comments_are_neutralized_too():
    theme = Theme.objects.create(name="Plain", slug="plain")
    css = snapshot_css(theme.snapshot(), f"capy-theme editor: preview of {ESCAPE}")
    assert css.splitlines()[0].count("*/") == 1
