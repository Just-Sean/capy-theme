"""Tests for the system font stacks (issue #24)."""

import pytest

from capy_theme.fonts import SYSTEM_STACKS
from capy_theme.models import Font, Theme
from capy_theme.publishing import publish
from capy_theme.stylesheet import render_css

pytestmark = pytest.mark.django_db


def test_the_migration_adds_every_stack():
    system = Font.objects.filter(source="system")
    assert set(system.values_list("family", flat=True)) == {name for name, _ in SYSTEM_STACKS}
    assert len(SYSTEM_STACKS) >= 10
    assert all(not font.files.exists() for font in system)


def test_system_sans_downloads_no_font_files():
    sans = Font.objects.get(family="System sans")
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"body": sans.pk}})
    css = render_css(publish(theme))
    assert "@font-face" not in css
    assert "url(" not in css
    assert "--font-sans: ui-sans-serif, system-ui, sans-serif;" in css


def test_stacks_are_used_as_given():
    mono = Font.objects.get(family="Monospace Code")
    theme = Theme.objects.create(name="Main", slug="main", settings={"fonts": {"mono": mono.pk}})
    css = render_css(publish(theme))
    assert f"--font-mono: {mono.fallback_stack};" in css
    assert '"Monospace Code"' not in css  # the stack's name isn't a real font family


def test_editor_and_admin_list_them():
    from capy_theme.admin import ThemeForm
    from capy_theme.editor import controls

    assert "System serif" in [f["family"] for f in controls()["fonts"]]
    labels = [label for _, label in ThemeForm().fields["font_heading"].choices]
    assert "Didone" in labels
