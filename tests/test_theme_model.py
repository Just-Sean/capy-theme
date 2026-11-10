"""Tests for the Theme model, its validation and its admin (issue #5)."""

import uuid

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.urls import reverse

from capy_theme.admin import ThemeForm
from capy_theme.models import Theme
from capy_theme.validation import validate_settings

pytestmark = pytest.mark.django_db


def make_theme(**kwargs):
    fields = {"name": "Main", "slug": "main"} | kwargs
    return Theme.objects.create(**fields)


# The model


def test_new_theme_has_defaults():
    theme = make_theme()
    assert theme.light_base == "light"
    assert theme.dark_base == "dark"
    assert theme.settings == {}
    assert isinstance(theme.public_id, uuid.UUID)
    assert theme.created_at is not None
    assert theme.updated_at is not None
    assert str(theme) == "Main"


def test_public_ids_are_unique_per_theme():
    assert make_theme().public_id != make_theme(name="Other", slug="other").public_id


def test_name_must_be_unique():
    make_theme()
    with pytest.raises(IntegrityError):
        make_theme(slug="main-2")


def test_slug_must_be_unique():
    make_theme()
    with pytest.raises(IntegrityError):
        make_theme(name="Main 2")


def test_bases_can_be_any_theme_of_the_matching_type():
    theme = make_theme(light_base="cupcake", dark_base="synthwave")
    assert (theme.light_base, theme.dark_base) == ("cupcake", "synthwave")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("light_base", "synthwave"),  # a dark theme as the light base
        ("dark_base", "cupcake"),  # a light theme as the dark base
        ("light_base", "not-a-theme"),
    ],
)
def test_wrong_or_unknown_base_cant_be_saved(field, value):
    with pytest.raises(ValidationError) as excinfo:
        make_theme(**{field: value})
    assert field in excinfo.value.message_dict
    assert not Theme.objects.exists()


def test_base_must_be_allowed_by_project_setting(settings):
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]
    with pytest.raises(ValidationError):
        make_theme(light_base="cupcake")


# Settings schema


def test_empty_settings_are_valid():
    validate_settings({})


@pytest.mark.parametrize("bad", [{"not_a_setting": 1}, [], "text", None])
def test_bad_settings_are_rejected(bad):
    with pytest.raises(ValidationError):
        validate_settings(bad)


def test_bad_settings_cant_be_saved():
    with pytest.raises(ValidationError, match="not_a_setting"):
        make_theme(settings={"not_a_setting": 1})
    assert not Theme.objects.exists()


def test_bad_settings_cant_be_saved_on_update():
    theme = make_theme()
    theme.settings = {"not_a_setting": 1}
    with pytest.raises(ValidationError):
        theme.save()
    theme.refresh_from_db()
    assert theme.settings == {}


# The admin form


def form_data(**kwargs):
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "settings": "{}",
        # The published-revisions inline's management form (it has no rows here).
        "revisions-TOTAL_FORMS": "0",
        "revisions-INITIAL_FORMS": "0",
        "revisions-MIN_NUM_FORMS": "0",
        "revisions-MAX_NUM_FORMS": "1000",
    }
    return data | kwargs


def test_form_offers_only_matching_themes_as_bases():
    form = ThemeForm()
    light = {value for value, _ in form.fields["light_base"].choices}
    dark = {value for value, _ in form.fields["dark_base"].choices}
    assert {"light", "cupcake"} <= light
    assert "synthwave" not in light
    assert {"dark", "synthwave"} <= dark
    assert "cupcake" not in dark
    assert form.fields["light_base"].initial == "light"
    assert form.fields["dark_base"].initial == "dark"


def test_form_follows_project_setting(settings):
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]
    form = ThemeForm()
    assert [value for value, _ in form.fields["light_base"].choices] == ["light"]
    assert [value for value, _ in form.fields["dark_base"].choices] == ["dark"]


def test_form_saves_a_valid_theme():
    form = ThemeForm(data=form_data(light_base="cupcake", dark_base="dracula"))
    assert form.is_valid(), form.errors
    theme = form.save()
    assert (theme.light_base, theme.dark_base) == ("cupcake", "dracula")


def test_form_rejects_too_long_branding():
    form = ThemeForm(data=form_data(site_name="x" * 101))
    assert not form.is_valid()
    assert "site_name" in form.errors


# The admin pages


@pytest.fixture
def admin_client_logged_in(client, django_user_model):
    user = django_user_model.objects.create_superuser("admin", "admin@example.com", "pw")
    client.force_login(user)
    return client


def test_admin_list_and_add_pages_load(admin_client_logged_in):
    make_theme()
    response = admin_client_logged_in.get(reverse("admin:capy_theme_theme_changelist"))
    assert response.status_code == 200
    assert b"Main" in response.content
    response = admin_client_logged_in.get(reverse("admin:capy_theme_theme_add"))
    assert response.status_code == 200


def test_admin_creates_a_theme(admin_client_logged_in):
    response = admin_client_logged_in.post(
        reverse("admin:capy_theme_theme_add"),
        form_data(name="Holiday", slug="holiday", light_base="cupcake", dark_base="dracula"),
    )
    assert response.status_code == 302, response.content
    theme = Theme.objects.get(slug="holiday")
    assert (theme.light_base, theme.dark_base) == ("cupcake", "dracula")
