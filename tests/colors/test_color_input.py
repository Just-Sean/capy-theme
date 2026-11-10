"""Tests for entering colours any common way (issue #15)."""

from pathlib import Path

import pytest
from django.urls import reverse

from capy_theme.admin.theme_form import ThemeForm
from capy_theme.colors.fields import ColorField
from capy_theme.colors.maths import to_hex, to_oklch
from capy_theme.models import Theme

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    ("given", "stored"),
    [
        ("#3b82f6", "oklch(62.31% 0.188 259.81)"),
        ("rgb(59 130 246)", "oklch(62.31% 0.188 259.81)"),
        ("oklch(62% 0.19 260)", "oklch(62% 0.19 260)"),
        ("hsl(217 91% 60%)", "oklch(62.61% 0.1859 259.6)"),
        ("#fff", "oklch(100% 0 0)"),
        ("red", "oklch(62.8% 0.2577 29.23)"),
        ("  #3B82F6  ", "oklch(62.31% 0.188 259.81)"),
    ],
)
def test_any_common_format_is_stored_as_oklch(given, stored):
    assert to_oklch(given) == stored
    assert ColorField().clean(given) == stored


def test_transparency_is_kept():
    assert to_oklch("rgb(0 0 0 / 50%)") == "oklch(0% 0 0 / 0.5)"


@pytest.mark.parametrize("bad", ["bright pink", "#12", "rgb(1 2)", "oklch()"])
def test_non_colours_are_rejected(bad):
    with pytest.raises(ValueError):
        to_oklch(bad)


def test_hex_for_the_picker():
    assert to_hex("oklch(62.31% 0.188 259.81)") == "#3b82f6"
    assert to_hex("oklch(0% 0 0 / 0.5)", alpha=False) == "#000000"


def form_data(**kwargs):
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
    }
    return data | kwargs


def test_the_issue_check_three_formats_save_and_show_as_oklch():
    form = ThemeForm(
        data=form_data(
            color_light_primary="#3b82f6",
            color_light_secondary="rgb(59 130 246)",
            color_light_accent="oklch(62% 0.19 260)",
        )
    )
    assert form.is_valid(), form.errors
    theme = form.save()
    assert theme.settings["colors"]["light"] == {
        "primary": "oklch(62.31% 0.188 259.81)",
        "secondary": "oklch(62.31% 0.188 259.81)",
        "accent": "oklch(62% 0.19 260)",
    }
    shown = ThemeForm(instance=theme)
    assert shown.fields["color_light_primary"].initial == "oklch(62.31% 0.188 259.81)"


def test_widget_has_a_colour_picker_matching_the_value():
    html = ColorField().widget.render("c", "oklch(62.31% 0.188 259.81)", {"id": "id_c"})
    assert 'type="text"' in html
    assert 'type="color" value="#3b82f6" data-capy-color-for="id_c"' in html


def test_empty_picker_shows_the_base_colour():
    theme = Theme.objects.create(name="Main", slug="main", light_base="cupcake")
    form = ThemeForm(instance=theme)
    html = str(form["color_light_primary"])
    placeholder = form.fields["color_light_primary"].widget.attrs["placeholder"]
    assert f'value="{to_hex(placeholder, alpha=False)}"' in html


def test_admin_page_loads_the_picker_script(client, django_user_model):
    client.force_login(django_user_model.objects.create_superuser("s", "s@example.com", "pw"))
    theme = Theme.objects.create(name="Main", slug="main")
    content = client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content.decode()
    assert "capy_theme/admin/color_input.js" in content
    assert 'type="color"' in content


def test_picker_script_is_bundled():
    script = (
        Path(__file__).resolve().parents[2]
        / "src/capy_theme/static/capy_theme/admin/color_input.js"
    )
    assert "data-capy-color-for" in script.read_text()
