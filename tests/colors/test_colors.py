"""Tests for color overrides (issue #14)."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from capy_theme.admin.form_colors import color_field_name
from capy_theme.admin.theme_admin import ThemeAdmin
from capy_theme.admin.theme_form import ThemeForm
from capy_theme.colors.names import COLOR_GROUPS, COLOR_NAMES, label
from capy_theme.colors.values import effective_values
from capy_theme.css.stylesheet import render_css
from capy_theme.models import Theme
from capy_theme.themes.catalog import THEMES
from capy_theme.themes.publishing import publish
from capy_theme.themes.validation import validate_settings

pytestmark = pytest.mark.django_db

PINK = "oklch(65% 0.24 350)"
TEAL = "oklch(70% 0.12 190)"


def test_there_are_20_colors_in_three_groups():
    assert len(COLOR_NAMES) == 20 == len(set(COLOR_NAMES))
    assert list(COLOR_GROUPS) == ["Basic", "Advanced", "Expert"]
    # Every daisyUI color variable is covered.
    daisy = {
        k.removeprefix("--color-") for k in THEMES["light"]["values"] if k.startswith("--color-")
    }
    assert set(COLOR_NAMES) == daisy


def test_labels():
    assert label("primary") == "Primary"
    assert label("primary-content") == "Primary text"
    assert label("base-100") == "Background"


# Settings schema


def test_schema_accepts_color_overrides():
    validate_settings({"colors": {"primary": PINK, "base-100": TEAL}})


@pytest.mark.parametrize(
    "bad",
    [
        {"colors": {"not-a-color": PINK}},
        {"colors": {"primary": "pink"}},
        {"colors": {"sepia": PINK}},
        # The old per-mode shape ({"light": {...}}) is no longer valid: a theme is
        # a single scheme, so colors is flat.
        {"colors": {"primary": {"light": PINK}}},
        {"colors": {"primary": 5}},
    ],
)
def test_schema_rejects_bad_overrides(bad):
    with pytest.raises(ValidationError):
        validate_settings(bad)


# Merging over the base


def theme_with(colors, base="light"):
    theme = Theme.objects.create(name="Main", slug="main", base=base, settings={"colors": colors})
    return publish(theme)


def test_overrides_are_merged_over_the_base():
    revision = theme_with({"primary": PINK, "primary-content": TEAL})
    values = effective_values(revision.snapshot)
    assert values["--color-primary"] == PINK
    assert values["--color-primary-content"] == TEAL
    # Everything else comes from the base theme.
    base_light = THEMES["light"]["values"]
    changed = {"--color-primary", "--color-primary-content"}
    assert {k: v for k, v in values.items() if k not in changed} == {
        k: v for k, v in base_light.items() if k not in changed
    }


def test_each_theme_overrides_its_own_scheme():
    # A theme is a single scheme; a light theme and a dark theme each override
    # their own base.
    light = theme_with({"primary": PINK}, base="light")
    Theme.objects.all().delete()
    dark = theme_with({"primary": TEAL}, base="dracula")
    assert effective_values(light.snapshot)["--color-primary"] == PINK
    assert effective_values(dark.snapshot)["--color-primary"] == TEAL


def test_stylesheet_uses_the_override_and_nothing_else_changes():
    plain = render_css(theme_with({}))
    Theme.objects.all().delete()
    overridden = render_css(theme_with({"primary": PINK, "primary-content": TEAL}))
    changed = [
        (a, b)
        for a, b in zip(plain.splitlines(), overridden.splitlines(), strict=True)
        if a != b and "--capy-focus" not in b  # the focus color may follow primary (2.7)
    ]
    # Only primary and its text color change, in the :root and capy-light blocks.
    assert sorted(b.strip() for _, b in changed) == sorted(
        [f"--color-primary: {PINK};", f"--color-primary-content: {TEAL};"] * 2
    )


def test_changing_a_color_is_an_unpublished_change():
    revision = theme_with({})
    theme = revision.theme
    theme.settings = {"colors": {"primary": PINK}}
    theme.save()
    assert theme.has_unpublished_changes


# The admin form


def form_data(**kwargs):
    data = {
        "name": "Main",
        "slug": "main",
        "base": "light",
    }
    return data | kwargs


def test_form_has_a_field_for_every_color():
    form = ThemeForm()
    for name in COLOR_NAMES:
        assert color_field_name(name) in form.fields


def test_form_stores_only_the_colors_set():
    form = ThemeForm(data=form_data(color_primary=PINK, color_base_100=TEAL))
    assert form.is_valid(), form.errors
    assert form.save().settings == {"colors": {"primary": PINK, "base-100": TEAL}}


def test_clearing_every_color_removes_them():
    theme = Theme.objects.create(name="Main", slug="main", settings={"colors": {"primary": PINK}})
    assert ThemeForm(instance=theme).fields["color_primary"].initial == PINK
    form = ThemeForm(data=form_data(), instance=theme)
    assert form.is_valid(), form.errors
    assert form.save().settings == {}


def test_form_rejects_a_bad_color():
    form = ThemeForm(data=form_data(color_primary="bright pink"))
    assert not form.is_valid()
    assert "color_primary" in form.errors


def test_blank_fields_show_the_base_color_as_a_hint():
    theme = Theme.objects.create(name="Main", slug="main", base="cupcake")
    field = ThemeForm(instance=theme).fields["color_primary"]
    assert field.widget.attrs["placeholder"] == THEMES["cupcake"]["values"]["--color-primary"]


def test_admin_groups_colors_basic_advanced_expert():
    names = [name for name, _ in ThemeAdmin.fieldsets]
    for group in ("Basic", "Advanced", "Expert"):
        assert f"Colors: {group}" in names
    options = dict(ThemeAdmin.fieldsets)
    assert options["Colors: Basic"]["classes"] == ["collapse"]  # every section folds
    assert options["Colors: Expert"]["classes"] == ["collapse"]


def test_admin_page_shows_and_saves_colors(client, django_user_model):
    user = django_user_model.objects.create_superuser("sean", "s@example.com", "pw")
    client.force_login(user)
    theme = Theme.objects.create(name="Main", slug="main")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    assert b"Colors: Basic" in client.get(url).content
    data = form_data(color_primary=PINK) | {
        "assets-TOTAL_FORMS": "0",
        "assets-INITIAL_FORMS": "0",
        "revisions-TOTAL_FORMS": "0",
        "revisions-INITIAL_FORMS": "0",
        "revisions-MIN_NUM_FORMS": "0",
        "revisions-MAX_NUM_FORMS": "1000",
    }
    assert client.post(url, data).status_code == 302
    theme.refresh_from_db()
    assert theme.settings["colors"] == {"primary": PINK}
