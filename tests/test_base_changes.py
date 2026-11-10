"""Tests for the notice when daisyUI has changed or removed a theme's base (issue #78)."""

import re

import pytest
from django.urls import reverse

from capy_theme.builtin_themes import THEMES
from capy_theme.models import Theme
from capy_theme.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture
def theme():
    theme = Theme.objects.create(
        name="Main", slug="main", light_base="cupcake", dark_base="dracula"
    )
    publish(theme)
    return theme


def change_cupcake(monkeypatch):
    """Simulate a daisyUI update that changes cupcake's primary colour."""
    values = dict(THEMES["cupcake"]["values"], **{"--color-primary": "oklch(1% 0 0)"})
    monkeypatch.setitem(THEMES, "cupcake", {"scheme": "light", "values": values})


def test_no_notes_when_daisyui_is_unchanged(theme):
    assert theme.base_changes() == []


def test_no_notes_for_unpublished_theme():
    assert Theme.objects.create(name="Draft", slug="draft").base_changes() == []


def test_note_when_daisyui_changed_a_base(theme, monkeypatch):
    change_cupcake(monkeypatch)
    assert theme.base_changes() == [
        "daisyUI has changed “cupcake” since this theme was published. Your site keeps "
        "using the saved version. Publish again to use daisyUI's new one."
    ]


def test_note_when_daisyui_removed_a_base(theme, monkeypatch):
    monkeypatch.delitem(THEMES, "dracula")
    assert theme.base_changes() == [
        "“dracula” no longer exists in daisyUI. Your site keeps using the saved version. "
        "Choose a new dark base to publish changes."
    ]


def test_publishing_again_clears_the_note(theme, monkeypatch):
    change_cupcake(monkeypatch)
    publish(theme)
    assert theme.base_changes() == []


def test_a_project_setting_limiting_themes_is_not_flagged(theme, settings):
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]  # cupcake no longer offered
    assert theme.base_changes() == []


# The admin


@pytest.fixture
def admin(client, django_user_model):
    user = django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")
    client.force_login(user)
    return client


def test_admin_page_shows_the_note(admin, theme, monkeypatch):
    change_cupcake(monkeypatch)
    response = admin.get(reverse("admin:capy_theme_theme_change", args=[theme.pk]))
    assert "daisyUI has changed “cupcake”" in response.content.decode()


def test_admin_page_shows_the_removed_note(admin, theme, monkeypatch):
    monkeypatch.delitem(THEMES, "cupcake")
    response = admin.get(reverse("admin:capy_theme_theme_change", args=[theme.pk]))
    assert "“cupcake” no longer exists in daisyUI" in response.content.decode()


def base_changed_cell(admin):
    content = admin.get(reverse("admin:capy_theme_theme_changelist")).content.decode()
    match = re.search(r'<td class="field-base_changed_in_daisyui">.*?</td>', content, re.S)
    return match.group(0)


def test_admin_list_flags_affected_themes(admin, theme, monkeypatch):
    assert "icon-no.svg" in base_changed_cell(admin)
    change_cupcake(monkeypatch)
    assert "icon-yes.svg" in base_changed_cell(admin)
