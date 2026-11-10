"""Tests for custom CSS (issue #59)."""

import io

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.urls import reverse

from capy_theme.models import Theme
from capy_theme.portability.export import export_theme
from capy_theme.portability.importing import import_theme
from capy_theme.themes.active import activate
from capy_theme.themes.history import compare
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
CSS = ".hero { letter-spacing: 0.1em; }"


@pytest.fixture(autouse=True)
def clear():
    cache.clear()
    yield
    cache.clear()


def live(custom):
    theme = Theme.objects.create(name="Main", slug="main", settings={"custom_css": custom})
    revision = publish(theme)
    activate(theme)
    return theme, revision


def head(rf):
    return Template("{% load capy_theme %}{% theme_head %}").render(
        Context({"request": rf.get("/")})
    )


def test_published_custom_css_is_linked_after_the_theme_stylesheet(client, rf):
    _, revision = live({"css": CSS, "enabled": True})
    url = reverse("capy_theme:custom_css", args=[revision.css_version])
    html = head(rf)
    assert f'<link rel="stylesheet" href="{url}">' in html
    assert html.index(f"/theme/{revision.css_version}.css") < html.index(url)
    response = client.get(url)
    assert response.content.decode() == CSS + "\n"
    assert response["Content-Type"] == "text/css; charset=utf-8"
    assert "immutable" in response["Cache-Control"]


def test_the_issue_check_switched_off_it_isnt_loaded(client, rf):
    _, revision = live({"css": CSS, "enabled": False})
    assert "/theme/custom/" not in head(rf)
    url = reverse("capy_theme:custom_css", args=[revision.css_version])
    assert client.get(url).status_code == 404


def test_empty_custom_css_isnt_linked(rf):
    live({"css": "   ", "enabled": True})
    assert "/theme/custom/" not in head(rf)


def test_it_needs_publishing_like_everything_else(rf):
    theme, _ = live({"css": CSS, "enabled": True})
    theme.settings = {"custom_css": {"css": ".x{}", "enabled": True}}
    theme.save()
    assert theme.has_unpublished_changes
    new = publish(theme)
    assert reverse("capy_theme:custom_css", args=[new.css_version]) in head(rf)


def test_too_long_is_rejected():
    theme = Theme(name="T", slug="t", settings={"custom_css": {"css": "a" * 100_001}})
    with pytest.raises(ValidationError):
        theme.save()


# Who can see and change it


def staff(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user("s", password="pw", is_staff=True)
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    client.force_login(user)
    return client


def form_data(**extra):
    return {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "visitors_can_switch": "on",
        "assets-TOTAL_FORMS": "0",
        "assets-INITIAL_FORMS": "0",
        "revisions-TOTAL_FORMS": "0",
        "revisions-INITIAL_FORMS": "0",
    } | extra


def test_the_issue_check_without_the_permission_it_cant_be_seen_or_changed(
    client, django_user_model
):
    theme, _ = live({"css": CSS, "enabled": True})
    staff(client, django_user_model, "view_theme", "change_theme")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    page = client.get(url).content.decode()
    assert 'name="custom_css"' not in page
    assert "letter-spacing" not in page  # not even in the stored-settings box
    assert "(on, 32 characters)" in page
    # Saving the form (even trying to send the field) leaves it as it was.
    response = client.post(url, form_data(custom_css="body{display:none}"))
    assert response.status_code == 302
    theme.refresh_from_db()
    assert theme.settings["custom_css"] == {"css": CSS, "enabled": True}


def test_with_the_permission_it_can_be_edited(client, django_user_model):
    theme, _ = live({"css": CSS, "enabled": True})
    staff(client, django_user_model, "view_theme", "change_theme", "edit_custom_css")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    page = client.get(url).content.decode()
    assert 'name="custom_css"' in page and "letter-spacing" in page
    client.post(url, form_data(custom_css=".new { color: red; }"))  # switch unticked
    theme.refresh_from_db()
    assert theme.settings["custom_css"] == {"css": ".new { color: red; }", "enabled": False}


def test_the_editor_never_receives_it(client, django_user_model):
    theme, _ = live({"css": CSS, "enabled": True})
    staff(client, django_user_model, "change_theme", "edit_custom_css")
    state = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert "custom_css" not in state["settings"]
    url = reverse("capy_theme:editor_save", args=[theme.pk])
    client.post(url, {"settings": {"colors": {}}}, content_type="application/json")
    theme.refresh_from_db()
    assert theme.settings["custom_css"]["css"] == CSS  # saving from the editor keeps it


def test_revision_comparison_shows_only_a_summary():
    theme, first = live({"css": CSS, "enabled": True})
    theme.settings = {"custom_css": {"css": CSS, "enabled": False}}
    theme.save()
    second = publish(theme)
    rows = {row["name"]: row for row in compare(first, second)}
    assert rows["Custom CSS"] == {
        "name": "Custom CSS",
        "older": "on, 32 characters",
        "newer": "off, 32 characters",
    }


def test_imports_drop_it_unless_the_importer_may_edit_it():
    theme, _ = live({"css": CSS, "enabled": True})
    data = export_theme(theme)
    assert "custom_css" not in import_theme(io.BytesIO(data), keep_custom_css=False).settings
    assert import_theme(io.BytesIO(data)).settings["custom_css"]["css"] == CSS


def test_an_empty_custom_css_isnt_stored(client, django_user_model):
    theme = Theme.objects.create(name="Main", slug="main")
    staff(client, django_user_model, "view_theme", "change_theme", "edit_custom_css")
    url = reverse("admin:capy_theme_theme_change", args=[theme.pk])
    client.post(url, form_data(custom_css="   "))  # switch unticked too
    theme.refresh_from_db()
    assert "custom_css" not in theme.settings
