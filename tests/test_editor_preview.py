"""Tests for the editor's draft preview endpoint (issue #96)."""

import json

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.urls import reverse

from capy_theme.colors import effective_values
from capy_theme.editor import apply_changes
from capy_theme.models import Theme, ThemeRevision
from capy_theme.publishing import publish
from capy_theme.stylesheet import render_css

pytestmark = pytest.mark.django_db
PINK = "oklch(65% 0.24 350)"


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def editor_client(client, django_user_model):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename="change_theme")
    )
    client.force_login(user)
    return client


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy"})


def post(client, theme, data):
    return client.post(
        reverse("capy_theme:editor_preview", args=[theme.pk]),
        data=json.dumps(data),
        content_type="application/json",
    )


def test_preview_returns_css_values_and_contrast(editor_client, theme):
    response = post(editor_client, theme, {"settings": {"colors": {"light": {"primary": PINK}}}})
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    data = response.json()
    assert f"--color-primary: {PINK};" in data["css"]
    assert data["values"]["light"]["--color-primary"] == PINK
    assert len(data["contrast"]["light"]) == 11
    assert data["settings"]["site_name"] == "Capy"  # untouched settings are kept


def test_derived_values_match_what_publishing_would_produce(editor_client, theme):
    changes = {"settings": {"colors": {"light": {"primary": "oklch(25% 0.12 260)"}}}}
    data = post(editor_client, theme, changes).json()
    theme.settings = {"site_name": "Capy", "colors": {"light": {"primary": "oklch(25% 0.12 260)"}}}
    theme.save()
    revision = publish(theme)
    published = effective_values(revision.snapshot, "light")
    assert data["values"]["light"] == published
    assert data["css"].splitlines()[1:] == render_css(revision).splitlines()[1:]


def test_any_colour_format_is_accepted(editor_client, theme):
    data = post(
        editor_client, theme, {"settings": {"colors": {"light": {"primary": "#3b82f6"}}}}
    ).json()
    assert data["values"]["light"]["--color-primary"] == "oklch(62.31% 0.188 259.81)"


def test_bases_and_shape_can_change(editor_client, theme):
    data = post(
        editor_client,
        theme,
        {"light_base": "cupcake", "settings": {"shape": {"radius_box": 0}}},
    ).json()
    assert "--radius-box: 0rem;" in data["css"]


def test_preview_writes_nothing(editor_client, theme):
    before = (theme.light_base, dict(theme.settings), Theme.objects.get(pk=theme.pk).updated_at)
    post(
        editor_client,
        theme,
        {"light_base": "cupcake", "settings": {"colors": {"light": {"primary": PINK}}}},
    )
    fresh = Theme.objects.get(pk=theme.pk)
    assert (fresh.light_base, fresh.settings, fresh.updated_at) == before
    assert not ThemeRevision.objects.exists()


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"settings": {"colors": {"light": {"primary": "bright pink"}}}}, "isn't a colour"),
        ({"light_base": "synthwave"}, "light daisyUI theme"),
        ({"settings": {"shape": {"radius_box": 99}}}, "99"),
        ({"settings": {"colors": {"light": {"sparkle": PINK}}}}, "sparkle"),
    ],
)
def test_invalid_values_are_listed(editor_client, theme, data, message):
    response = post(editor_client, theme, data)
    assert response.status_code == 400
    assert any(message in error for error in response.json()["errors"])


def test_bad_json_is_refused(editor_client, theme):
    response = editor_client.post(
        reverse("capy_theme:editor_preview", args=[theme.pk]),
        data="nope",
        content_type="application/json",
    )
    assert response.status_code == 400


def test_only_post(editor_client, theme):
    assert (
        editor_client.get(reverse("capy_theme:editor_preview", args=[theme.pk])).status_code == 405
    )


def test_refused_without_permission(client, django_user_model, theme):
    client.force_login(django_user_model.objects.create_user("v", password="pw", is_staff=True))
    assert post(client, theme, {}).status_code == 403


def test_csrf_is_required(django_user_model, theme):
    from django.test import Client

    user = django_user_model.objects.create_superuser("root", "r@example.com", "pw")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    assert post(client, theme, {}).status_code == 403


def test_apply_changes_leaves_the_theme_alone(theme):
    draft = apply_changes(theme, {"light_base": "cupcake"})
    assert draft.light_base == "cupcake"
    assert theme.light_base == "light"


def test_mount_passes_the_preview_url_and_csrf_token(editor_client, theme):
    content = editor_client.get(f"/theme/showcase/?edit={theme.pk}").content.decode()
    assert f'data-preview-url="{reverse("capy_theme:editor_preview", args=[theme.pk])}"' in content
    assert 'data-csrf-token="' in content
