"""Tests for saving and publishing from the editor (issue #98)."""

import json

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.urls import reverse

from capy_theme.models import Theme, ThemeRevision
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
PINK = "oklch(65% 0.24 350)"


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


def login(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename__in=codenames)
    )
    client.force_login(user)
    return user


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main", settings={"site_name": "Capy"})


def post(client, name, theme, data):
    return client.post(
        reverse(f"capy_theme:editor_{name}", args=[theme.pk]),
        data=json.dumps(data),
        content_type="application/json",
    )


# Save draft


def test_save_stores_the_draft_and_keeps_other_settings(client, django_user_model, theme):
    login(client, django_user_model, "change_theme")
    response = post(
        client,
        "save",
        theme,
        {"light_base": "cupcake", "settings": {"colors": {"light": {"primary": "#3b82f6"}}}},
    )
    assert response.status_code == 200
    theme.refresh_from_db()
    assert theme.light_base == "cupcake"
    assert theme.settings == {
        "site_name": "Capy",
        "colors": {"light": {"primary": "oklch(62.31% 0.188 259.81)"}},
    }
    assert response.json()["state"]["has_unpublished_changes"] is True


def test_saving_doesnt_publish(client, django_user_model, theme):
    login(client, django_user_model, "change_theme")
    publish(theme)
    activate(theme)
    post(client, "save", theme, {"settings": {"colors": {"light": {"primary": PINK}}}})
    theme.refresh_from_db()
    assert theme.live_revision.number == 1
    assert "colors" not in theme.live_revision.snapshot["settings"]


def test_save_refuses_invalid_values_and_changes_nothing(client, django_user_model, theme):
    login(client, django_user_model, "change_theme")
    response = post(client, "save", theme, {"settings": {"colors": {"light": {"primary": "nope"}}}})
    assert response.status_code == 400
    theme.refresh_from_db()
    assert theme.settings == {"site_name": "Capy"}


def test_save_needs_change_permission(client, django_user_model, theme):
    login(client, django_user_model, "view_theme")
    assert post(client, "save", theme, {}).status_code == 403


# Publish


def test_publish_needs_the_publish_permission(client, django_user_model, theme):
    login(client, django_user_model, "change_theme")
    assert post(client, "publish", theme, {}).status_code == 403
    assert not ThemeRevision.objects.exists()


def test_publish_makes_a_revision_with_the_note(client, django_user_model, theme):
    user = login(client, django_user_model, "change_theme", "publish_theme")
    response = post(client, "publish", theme, {"note": "From the editor"})
    assert response.status_code == 200
    assert response.json()["published"] == 1
    revision = theme.revisions.get()
    assert revision.note == "From the editor"
    assert revision.published_by == user
    assert response.json()["state"]["has_unpublished_changes"] is False


def test_publish_with_nothing_new_says_so(client, django_user_model, theme):
    login(client, django_user_model, "change_theme", "publish_theme")
    post(client, "publish", theme, {})
    response = post(client, "publish", theme, {})
    assert response.status_code == 409
    assert "Nothing to publish" in response.json()["errors"][0]


def test_publish_button_only_for_publishers(client, django_user_model, theme):
    login(client, django_user_model, "change_theme")
    state = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert state["can_publish"] is False
    assert "save" in state["urls"] and "publish" in state["urls"]


def test_mount_passes_save_and_publish_urls(client, django_user_model, theme):
    login(client, django_user_model, "change_theme")
    content = client.get(f"/page/?edit={theme.pk}").content.decode()
    assert f'data-save-url="{reverse("capy_theme:editor_save", args=[theme.pk])}"' in content
    assert f'data-publish-url="{reverse("capy_theme:editor_publish", args=[theme.pk])}"' in content


# Bad requests to the editor's endpoints (issue #181).


@pytest.mark.parametrize("name", ["preview", "save", "publish"])
@pytest.mark.parametrize("body", ["not json", "[1, 2]", '"text"'])
def test_bad_json_is_refused_and_nothing_changes(client, django_user_model, theme, name, body):
    login(client, django_user_model, "change_theme", "publish_theme")
    url = reverse(f"capy_theme:editor_{name}", args=[theme.pk])
    response = client.post(url, data=body, content_type="application/json")
    assert response.status_code == 400
    assert response.json()["errors"]
    theme.refresh_from_db()
    assert theme.settings == {"site_name": "Capy"}
    assert not ThemeRevision.objects.exists()


def test_publish_refuses_an_invalid_saved_draft(client, django_user_model, theme):
    # A draft can only be invalid if it was changed outside the app (e.g. in the
    # database directly); publishing it must fail cleanly, not make a revision.
    Theme.objects.filter(pk=theme.pk).update(settings={"colors": {"light": {"primary": 5}}})
    login(client, django_user_model, "change_theme", "publish_theme")
    response = post(client, "publish", theme, {})
    assert response.status_code == 400
    assert response.json()["errors"][0].startswith("Can't publish:")
    assert not ThemeRevision.objects.exists()


def test_a_real_collision_leaves_the_database_clean(client, django_user_model, theme, monkeypatch):
    # Someone else saves revision 1 between this publish choosing that number and
    # saving it: the database itself refuses the duplicate. Everything this publish
    # did is undone, and publishing works again afterwards.
    from capy_theme.themes import publishing

    real_css_version = publishing.css_version

    def someone_else_publishes_first(theme_pk, number, snapshot):
        ThemeRevision.objects.create(
            theme_id=theme_pk, number=number, snapshot=snapshot, css_version="other"
        )
        return real_css_version(theme_pk, number, snapshot)

    monkeypatch.setattr(publishing, "css_version", someone_else_publishes_first)
    login(client, django_user_model, "change_theme", "publish_theme")
    response = post(client, "publish", theme, {})
    assert response.status_code == 409
    theme.refresh_from_db()
    assert theme.live_revision is None
    monkeypatch.undo()
    assert post(client, "publish", theme, {}).status_code == 200
    assert list(theme.revisions.values_list("number", flat=True)) == [1]


def test_publishing_at_the_same_moment_as_someone_else(
    client, django_user_model, theme, monkeypatch
):
    # Two publishes racing for the same revision number: the second gets a clear 409.
    from django.db import IntegrityError

    def collide(*args, **kwargs):
        raise IntegrityError("unique_revision_number")

    monkeypatch.setattr("capy_theme.editor.views.publish", collide)
    login(client, django_user_model, "change_theme", "publish_theme")
    response = post(client, "publish", theme, {})
    assert response.status_code == 409
    assert "Someone else just published" in response.json()["errors"][0]
