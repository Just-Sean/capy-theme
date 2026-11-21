"""Colors and numbers that pass validation must never break pages (#240).

Before, oklch(50% 1e300 0) saved and published, then every page returned 500,
and NaN got past every minimum and maximum. These came from the QA review's
bug-proof tests.
"""

import io
import json
import zipfile

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.urls import reverse

from capy_theme.admin.theme_form import ThemeForm
from capy_theme.colors.color_math import to_oklch
from capy_theme.colors.fields import ColorField
from capy_theme.models import Theme
from capy_theme.portability.importing import import_theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db

HUGE = "oklch(50% 1e300 0)"


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


def form_data(**kwargs):
    data = {
        "name": "Main",
        "slug": "main",
        "base": "light",
    }
    return data | kwargs


def login(client, django_user_model):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename="change_theme")
    )
    client.force_login(user)


def editor_post(client, name, theme, body):
    return client.post(
        reverse(f"capy_theme:editor_{name}", args=[theme.pk]),
        data=body if isinstance(body, str) else json.dumps(body),
        content_type="application/json",
    )


# The color math


@pytest.mark.parametrize(
    "value",
    [
        HUGE,
        "lab(50 1e308 0)",  # overflows inside coloraide
        "oklch(1e400% 0 0)",  # infinite lightness
        "oklch(150% 0.1 20)",  # lighter than white
        "oklch(50% 0.9 20)",  # far more saturated than any real color
        "oklch(nan% 0 0)",
        "1e9",
    ],
)
def test_colors_outside_the_real_ranges_are_not_colors(value):
    with pytest.raises(ValueError):
        to_oklch(value)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("oklch(50% 0.2 -30)", "oklch(50% 0.2 330)"),  # a negative hue is the same as 330
        ("oklch(50% 0.2 400)", "oklch(50% 0.2 40)"),
        ("#FFF", "oklch(100% 0 0)"),
        ("#000", "oklch(0% 0 0)"),
        ("rgb(300 -20 0)", "oklch(70.75% 0.2947 28.75)"),  # outside sRGB, still real
        ("color(rec2020 0 1 0)", "oklch(82.98% 0.4683 152.6)"),  # the most saturated
        ("#ff000080", "oklch(62.8% 0.2577 29.23 / 0.502)"),
    ],
)
def test_real_colors_are_still_accepted(value, expected):
    assert to_oklch(value) == expected


# Every way in: the admin form, the editor, the model and an import


def test_the_color_field_refuses_an_overflowing_color():
    with pytest.raises(ValidationError):
        ColorField(required=False).clean("lab(50 1e308 0)")


@pytest.mark.parametrize("value", [HUGE, "oklch(1e400% 0 0)"])
def test_the_admin_form_refuses_a_color_too_strong_to_render(value):
    form = ThemeForm(data=form_data(color_primary=value))
    assert not form.is_valid()
    assert "color_primary" in form.errors


def test_the_admin_form_saves_a_negative_hue():
    form = ThemeForm(data=form_data(color_primary="oklch(50% 0.2 -30)"))
    assert form.is_valid(), form.errors
    theme = form.save()
    assert theme.settings["colors"]["primary"] == "oklch(50% 0.2 330)"


@pytest.mark.parametrize("name", ["preview", "save"])
def test_the_editor_refuses_a_color_too_strong_to_render_and_stores_nothing(
    client, django_user_model, name
):
    login(client, django_user_model)
    theme = Theme.objects.create(name="Main", slug="main")
    response = editor_post(client, name, theme, {"settings": {"colors": {"primary": HUGE}}})
    assert response.status_code == 400
    theme.refresh_from_db()
    assert "colors" not in theme.settings


def test_the_editor_saves_a_negative_hue(client, django_user_model):
    login(client, django_user_model)
    theme = Theme.objects.create(name="Main", slug="main")
    body = {"settings": {"colors": {"primary": "oklch(50% 0.2 -30)"}}}
    assert editor_post(client, "save", theme, body).status_code == 200


@pytest.mark.parametrize(
    "stored",
    [
        "oklch(50% 1" + "0" * 300 + " 0)",  # matched the old pattern [0-9.]+
        "oklch(50% 99999 0)",
        "oklch(1000% 0 0)",
    ],
)
def test_the_model_refuses_a_stored_color_that_would_break_pages(stored):
    with pytest.raises(ValidationError):
        Theme.objects.create(name="Main", slug="main", settings={"colors": {"primary": stored}})


def test_the_largest_color_the_model_accepts_still_renders_every_page(client):
    extreme = "oklch(999% 9.9999 999 / 999%)"
    theme = Theme.objects.create(
        name="Main", slug="main", settings={"colors": {"primary": extreme}}
    )
    activate(publish(theme).theme)
    assert client.get("/page/").status_code == 200


# NaN and infinity: JSON Schema's minimum and maximum never refuse NaN


@pytest.mark.parametrize(
    "settings",
    [
        {"shape": {"radius_box": float("nan")}},
        {"shape": {"radius_box": float("inf")}},
        {"type": {"scale": float("nan")}},
        {"type": {"base_size": float("-inf")}},
    ],
)
def test_the_model_refuses_nan_and_infinity(settings):
    with pytest.raises(ValidationError, match="isn't a number"):
        Theme.objects.create(name="Main", slug="main", settings=settings)


@pytest.mark.parametrize(
    "name, body",
    [
        ("save", '{"settings": {"shape": {"radius_box": NaN}}}'),
        ("preview", '{"settings": {"type": {"base_size": NaN}}}'),
        ("save", '{"settings": {"shape": {"radius_box": Infinity}}}'),
    ],
)
def test_the_editor_answers_400_for_nan_and_infinity(client, django_user_model, name, body):
    login(client, django_user_model)
    theme = Theme.objects.create(name="Main", slug="main")
    response = editor_post(client, name, theme, body)
    assert response.status_code == 400
    theme.refresh_from_db()
    assert "shape" not in theme.settings


def test_an_import_with_nan_is_refused():
    manifest = (
        '{"format": "capy-theme-export/1", "fonts": {}, "images": {}, "theme": {"name": "T",'
        ' "slug": "t", "base": "light",'
        ' "settings": {"shape": {"radius_box": NaN}}}}'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("theme.json", manifest)
    buffer.seek(0)
    with pytest.raises(ValidationError):
        import_theme(buffer)
    assert not Theme.objects.exists()


def test_an_import_with_a_huge_color_is_refused():
    manifest = json.dumps(
        {
            "format": "capy-theme-export/1",
            "fonts": {},
            "images": {},
            "theme": {
                "name": "T",
                "slug": "t",
                "base": "light",
                "settings": {"colors": {"primary": "oklch(50% 1" + "0" * 300 + " 0)"}},
            },
        }
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("theme.json", manifest)
    buffer.seek(0)
    with pytest.raises(ValidationError):
        import_theme(buffer)
    assert not Theme.objects.exists()
