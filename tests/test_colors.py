"""Tests for colour overrides (issue #14)."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from capy_theme.admin import ThemeAdmin, ThemeForm, color_field_name
from capy_theme.builtin_themes import THEMES
from capy_theme.colors import COLOR_GROUPS, COLOR_NAMES, effective_values, label
from capy_theme.models import Theme
from capy_theme.publishing import publish
from capy_theme.stylesheet import render_css
from capy_theme.validation import validate_settings

pytestmark = pytest.mark.django_db

PINK = "oklch(65% 0.24 350)"
TEAL = "oklch(70% 0.12 190)"


def test_there_are_20_colours_in_three_groups():
    assert len(COLOR_NAMES) == 20 == len(set(COLOR_NAMES))
    assert list(COLOR_GROUPS) == ["Basic", "Advanced", "Expert"]
    # Every daisyUI colour variable is covered.
    daisy = {
        k.removeprefix("--color-") for k in THEMES["light"]["values"] if k.startswith("--color-")
    }
    assert set(COLOR_NAMES) == daisy


def test_labels():
    assert label("primary") == "Primary"
    assert label("primary-content") == "Primary text"
    assert label("base-100") == "Background"


# Settings schema


def test_schema_accepts_colour_overrides():
    validate_settings({"colors": {"light": {"primary": PINK}, "dark": {"base-100": TEAL}}})


@pytest.mark.parametrize(
    "bad",
    [
        {"colors": {"light": {"not-a-colour": PINK}}},
        {"colors": {"light": {"primary": "pink"}}},
        {"colors": {"sepia": {"primary": PINK}}},
        {"colors": {"light": {"primary": 5}}},
    ],
)
def test_schema_rejects_bad_overrides(bad):
    with pytest.raises(ValidationError):
        validate_settings(bad)


# Merging over the base


def theme_with(colors):
    theme = Theme.objects.create(
        name="Main", slug="main", light_base="light", dark_base="dark", settings={"colors": colors}
    )
    return publish(theme)


def test_overrides_are_merged_over_the_base():
    revision = theme_with({"light": {"primary": PINK, "primary-content": TEAL}})
    light = effective_values(revision.snapshot, "light")
    dark = effective_values(revision.snapshot, "dark")
    assert light["--color-primary"] == PINK
    assert light["--color-primary-content"] == TEAL
    # Everything else comes from the base themes.
    base_light = THEMES["light"]["values"]
    changed = {"--color-primary", "--color-primary-content"}
    assert {k: v for k, v in light.items() if k not in changed} == {
        k: v for k, v in base_light.items() if k not in changed
    }
    assert dark == THEMES["dark"]["values"]


def test_light_and_dark_are_separate():
    revision = theme_with({"light": {"primary": PINK}, "dark": {"primary": TEAL}})
    assert effective_values(revision.snapshot, "light")["--color-primary"] == PINK
    assert effective_values(revision.snapshot, "dark")["--color-primary"] == TEAL


def test_stylesheet_uses_the_override_and_nothing_else_changes():
    plain = render_css(theme_with({}))
    Theme.objects.all().delete()
    overridden = render_css(theme_with({"light": {"primary": PINK, "primary-content": TEAL}}))
    changed = [
        (a, b)
        for a, b in zip(plain.splitlines(), overridden.splitlines(), strict=True)
        if a != b and "--capy-focus" not in b  # the focus colour may follow primary (2.7)
    ]
    # Only primary and its text colour change, in the light :root and capy-light blocks.
    assert sorted(b.strip() for _, b in changed) == sorted(
        [f"--color-primary: {PINK};", f"--color-primary-content: {TEAL};"] * 2
    )


def test_changing_a_colour_is_an_unpublished_change():
    revision = theme_with({})
    theme = revision.theme
    theme.settings = {"colors": {"light": {"primary": PINK}}}
    theme.save()
    assert theme.has_unpublished_changes


# The admin form


def form_data(**kwargs):
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
    }
    return data | kwargs


def test_form_has_a_field_for_every_colour_in_both_modes():
    form = ThemeForm()
    for scheme in ("light", "dark"):
        for name in COLOR_NAMES:
            assert color_field_name(scheme, name) in form.fields


def test_form_stores_only_the_colours_set():
    form = ThemeForm(data=form_data(color_light_primary=PINK, color_dark_base_100=TEAL))
    assert form.is_valid(), form.errors
    assert form.save().settings == {
        "colors": {"light": {"primary": PINK}, "dark": {"base-100": TEAL}}
    }


def test_clearing_every_colour_removes_them():
    theme = Theme.objects.create(
        name="Main", slug="main", settings={"colors": {"light": {"primary": PINK}}}
    )
    assert ThemeForm(instance=theme).fields["color_light_primary"].initial == PINK
    form = ThemeForm(data=form_data(), instance=theme)
    assert form.is_valid(), form.errors
    assert form.save().settings == {}


def test_form_rejects_a_bad_colour():
    form = ThemeForm(data=form_data(color_light_primary="bright pink"))
    assert not form.is_valid()
    assert "color_light_primary" in form.errors


def test_blank_fields_show_the_base_colour_as_a_hint():
    theme = Theme.objects.create(name="Main", slug="main", light_base="cupcake")
    field = ThemeForm(instance=theme).fields["color_light_primary"]
    assert field.widget.attrs["placeholder"] == THEMES["cupcake"]["values"]["--color-primary"]


def test_admin_groups_colours_basic_advanced_expert():
    names = [name for name, _ in ThemeAdmin.fieldsets]
    for scheme in ("Light", "Dark"):
        for group in ("Basic", "Advanced", "Expert"):
            assert f"{scheme} colours: {group}" in names
    options = dict(ThemeAdmin.fieldsets)
    assert options["Light colours: Basic"]["classes"] == []
    assert options["Light colours: Expert"]["classes"] == ["collapse"]


def test_admin_page_shows_and_saves_colours(client, django_user_model):
    user = django_user_model.objects.create_superuser("sean", "s@example.com", "pw")
    client.force_login(user)
    theme = Theme.objects.create(name="Main", slug="main")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    assert b"Light colours: Basic" in client.get(url).content
    data = form_data(color_light_primary=PINK) | {
        "assets-TOTAL_FORMS": "0",
        "assets-INITIAL_FORMS": "0",
        "revisions-TOTAL_FORMS": "0",
        "revisions-INITIAL_FORMS": "0",
        "revisions-MIN_NUM_FORMS": "0",
        "revisions-MAX_NUM_FORMS": "1000",
    }
    assert client.post(url, data).status_code == 302
    theme.refresh_from_db()
    assert theme.settings["colors"] == {"light": {"primary": PINK}}
