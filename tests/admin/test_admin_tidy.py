"""Tests for the tidied admin form (issue #41)."""

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from capy_theme.admin.theme_admin import ThemeAdmin
from capy_theme.admin.theme_form import ThemeForm
from capy_theme.models import Theme

pytestmark = pytest.mark.django_db


def test_sections_are_in_a_clear_order():
    names = [name for name, _ in ThemeAdmin.fieldsets]
    order = [
        "Publishing",
        "Base themes",
        "Branding",
        "Light colors: Basic",
        "Contrast",
        "Shape and effects",
        "Mode",
        "Advanced",
    ]
    assert [names.index(n) for n in order] == sorted(names.index(n) for n in order)
    assert names[0] is None  # name and slug first


def test_every_setting_is_reachable():
    in_sections = {f for _, options in ThemeAdmin.fieldsets for f in options["fields"]}
    form_fields = set(ThemeForm().fields)
    assert form_fields <= in_sections
    assert {"publish_status", "contrast_table", "settings_json"} <= in_sections


def test_advanced_parts_are_folded():
    options = dict(ThemeAdmin.fieldsets)
    for name in ("Advanced", "Contrast", "Shape and effects", "Light colors: Expert"):
        assert "collapse" in options[name]["classes"], name


def login(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename__in=codenames)
    )
    client.force_login(user)


def page(client, theme):
    return client.get(reverse("admin:capy_theme_theme_change", args=[theme.pk])).content.decode()


def test_edit_live_opens_the_editor_on_the_home_page(client, django_user_model):
    login(client, django_user_model, "view_theme", "change_theme")
    theme = Theme.objects.create(name="Main", slug="main")
    assert f'href="/?edit={theme.pk}">Edit live</a>' in page(client, theme)


def test_no_edit_live_for_view_only_staff(client, django_user_model):
    login(client, django_user_model, "view_theme")
    theme = Theme.objects.create(name="Main", slug="main")
    assert ">Edit live</a>" not in page(
        client, theme
    )  # the tip text mentions it; the link isn't shown
