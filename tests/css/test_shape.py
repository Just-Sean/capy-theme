"""Tests for shape and effects (issue #19)."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from capy_theme.admin.theme_form import ThemeForm
from capy_theme.colors.values import effective_values
from capy_theme.css.shape import EFFECTS, SIZES, shape_values
from capy_theme.css.stylesheet import render_css
from capy_theme.models import Theme
from capy_theme.themes.catalog import THEMES
from capy_theme.themes.publishing import publish
from capy_theme.themes.validation import validate_settings

pytestmark = pytest.mark.django_db


def test_every_daisyui_shape_value_is_covered():
    variables = {v[0] for v in SIZES.values()} | {v[0] for v in EFFECTS.values()}
    base = {k for k in THEMES["light"]["values"] if not k.startswith("--color-")}
    assert variables == base


def test_shape_values():
    assert shape_values(
        {"shape": {"radius_box": 0, "border": 1.5, "depth": False, "noise": True}}
    ) == {
        "--radius-box": "0rem",
        "--border": "1.5px",
        "--depth": "0",
        "--noise": "1",
    }


def test_schema_limits():
    validate_settings({"shape": {"radius_box": 0, "size_field": 0.25, "depth": True}})
    for bad in ({"radius_box": -1}, {"border": 10}, {"depth": "yes"}, {"corners": 1}):
        with pytest.raises(ValidationError):
            validate_settings({"shape": bad})


def publish_with(shape):
    theme = Theme.objects.create(name="Main", slug="main", settings={"shape": shape})
    return publish(theme)


def test_the_issue_check_box_radius_0_makes_cards_square():
    revision = publish_with({"radius_box": 0})
    css = render_css(revision)
    assert css.count("--radius-box: 0rem;") == 4  # light, dark, capy-light, capy-dark


def test_shape_applies_to_both_modes():
    revision = publish_with({"border": 2})
    assert effective_values(revision.snapshot, "light")["--border"] == "2px"
    assert effective_values(revision.snapshot, "dark")["--border"] == "2px"


def test_unset_shape_comes_from_the_base():
    revision = publish_with({"radius_box": 0})
    values = effective_values(revision.snapshot, "light")
    assert values["--radius-field"] == THEMES["light"]["values"]["--radius-field"]


def form_data(**kwargs):
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
    }
    return data | kwargs


def test_form_stores_only_the_shape_values_set():
    form = ThemeForm(data=form_data(shape_radius_box="0", shape_border="2", shape_noise="on"))
    assert form.is_valid(), form.errors
    assert form.save().settings == {"shape": {"radius_box": 0.0, "border": 2.0, "noise": True}}


def test_form_shows_current_values_and_base_hints():
    theme = Theme.objects.create(
        name="Main", slug="main", light_base="cupcake", settings={"shape": {"depth": False}}
    )
    form = ThemeForm(instance=theme)
    assert form.fields["shape_depth"].initial == "off"
    placeholder = form.fields["shape_radius_box"].widget.attrs["placeholder"]
    assert placeholder == THEMES["cupcake"]["values"]["--radius-box"].removesuffix("rem")


def test_form_rejects_out_of_range_values():
    form = ThemeForm(data=form_data(shape_radius_box="9"))
    assert not form.is_valid()
    assert "shape_radius_box" in form.errors


def test_clearing_shape_removes_it():
    theme = Theme.objects.create(name="Main", slug="main", settings={"shape": {"border": 2}})
    form = ThemeForm(data=form_data(), instance=theme)
    assert form.is_valid(), form.errors
    assert form.save().settings == {}


def test_admin_has_a_shape_section(client, django_user_model):
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    theme = Theme.objects.create(name="Main", slug="main")
    content = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content
    assert b"Shape and effects" in content
    assert b'name="shape_radius_box"' in content


def test_admin_size_fields_have_real_steps():
    # Issue #224: step "any" left the arrows stuck; each field steps by its data's step.
    form = ThemeForm()
    for name in SIZES:
        step = form.fields[f"shape_{name}"].widget.attrs["step"]
        assert step != "any"
        assert float(step) > 0
    assert form.fields["shape_size_field"].widget.attrs["step"] == "0.03125"
