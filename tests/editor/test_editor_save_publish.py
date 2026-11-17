"""Tests for saving and publishing from the editor (issue #98)."""

import json
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.urls import reverse

from capy_theme.models import Theme, ThemeRevision
from capy_theme.themes.active import activate, get_active_theme
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
STATIC_ACTIONS = (
    Path(__file__).resolve().parents[2]
    / "src/capy_theme/static/capy_theme/editor/controls/actions.js"
)
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


# Save, publish and activate from the editor (#273)


def test_editor_publish_can_also_activate(client, django_user_model):
    theme = Theme.objects.create(name="Main", slug="main")
    user = django_user_model.objects.create_user("pub", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(codename__in=["change_theme", "publish_theme"])
    )
    client.force_login(user)
    url = reverse("capy_theme:editor_publish", args=[theme.pk])
    state = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert state["is_default"] is False
    reply = client.post(url, {"activate": True}, content_type="application/json").json()
    assert (reply["published"], reply["activated"]) == (1, True)
    assert reply["state"]["is_default"] is True
    assert get_active_theme().pk == theme.pk
    # Nothing new to publish: activating still works (no new revision).
    other = Theme.objects.create(name="Other", slug="other")
    client.post(
        reverse("capy_theme:editor_publish", args=[other.pk]), {}, content_type="application/json"
    )
    reply = client.post(
        reverse("capy_theme:editor_publish", args=[other.pk]),
        {"activate": True},
        content_type="application/json",
    ).json()
    assert (reply["published"], reply["activated"]) == (None, True)
    assert get_active_theme().pk == other.pk and other.revisions.count() == 1


def test_editor_publish_without_activate_doesnt_activate(client, django_user_model):
    theme = Theme.objects.create(name="Main", slug="main")
    client.force_login(django_user_model.objects.create_superuser("r", "r@e.com", "pw"))
    url = reverse("capy_theme:editor_publish", args=[theme.pk])
    for value in (None, "yes", 1):  # only a real true activates
        body = {} if value is None else {"activate": value}
        client.post(url, body, content_type="application/json")
    assert theme.revisions.count() == 1 and get_active_theme() is None


def test_the_editor_has_the_three_buttons_with_descriptions():
    script = STATIC_ACTIONS.read_text()
    for words in (
        '"Save draft"',
        '"Save and publish"',
        '"Save, publish and activate"',
        "Visitors see nothing until you publish.",
        "makes this version of the theme live",
        "makes this the default theme",
        "Note for the history (optional, kept when you publish)",  # a visible label
        "This is already the default theme",
    ):
        assert words in script, words
    # No activate button when it already is the default theme, with a note saying so.
    assert "if (state.is_default) {" in script
    assert "All of the above" not in script  # each description makes sense on its own


def test_editor_publish_and_activate_says_when_a_schedule_shows_another_theme(
    client, django_user_model
):
    from datetime import timedelta

    from django.utils import timezone

    from capy_theme.models import ThemeAssignment

    login(client, django_user_model, "change_theme", "publish_theme")
    main = Theme.objects.create(name="Main", slug="main")
    sale = Theme.objects.create(name="Sale", slug="sale")
    publish(sale)
    now = timezone.now()
    ThemeAssignment.objects.create(
        theme=sale, starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1)
    )
    reply = post(client, "publish", main, {"activate": True}).json()
    assert reply["activated"] is True and reply["showing"] == "Sale"
    # It's the default theme now (no more activate button), though Sale shows for now.
    assert reply["state"]["is_default"] is True
    assert get_active_theme().pk == sale.pk
    assert "a theme schedule is showing" in STATIC_ACTIONS.read_text()


def test_the_editor_save_area_isnt_pinned():
    # Pinned, it covered the controls above it and could hide keyboard focus (#273).
    css = (STATIC_ACTIONS.parents[1] / "editor.css").read_text()
    actions = css[css.index(".capy-editor-actions {") :]
    assert "sticky" not in actions[: actions.index("}")]


def test_the_editor_keeps_the_publish_note_until_its_published():
    script = STATIC_ACTIONS.read_text()
    assert 'note.value = ui.publishNote || "";' in script  # back after a rebuild
    assert "ui.publishNote = note.value;" in script
    assert 'ui.publishNote = ""; // used' in script  # cleared once published
    assert "maxlength: String(state.note_max)" in script


def test_the_editor_state_has_the_note_limit(client, django_user_model):
    from capy_theme.themes.publishing import NOTE_MAX

    login(client, django_user_model, "change_theme")
    theme = Theme.objects.create(name="N", slug="n")
    state = client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert state["note_max"] == NOTE_MAX and "is_site_theme" not in state


# QA for #273: the editor's publish with "activate"


@pytest.mark.parametrize("value", ["true", 1, "1", None, False])
def test_only_a_json_true_activates(client, django_user_model, theme, value):
    login(client, django_user_model, "change_theme", "publish_theme")
    response = post(client, "publish", theme, {"activate": value})
    assert response.status_code == 200 and response.json()["activated"] is False
    assert theme.revisions.count() == 1 and get_active_theme() is None


def test_activate_needs_the_publish_permission(client, django_user_model, theme):
    login(client, django_user_model, "change_theme")
    assert post(client, "publish", theme, {"activate": True}).status_code == 403
    assert not ThemeRevision.objects.exists() and get_active_theme() is None


def test_activate_an_invalid_draft_activates_nothing(client, django_user_model, theme, settings):
    Theme.objects.filter(pk=theme.pk).update(light_base="cupcake")
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]
    login(client, django_user_model, "change_theme", "publish_theme")
    response = post(client, "publish", theme, {"activate": True})
    assert response.status_code == 400 and "Can't publish" in response.json()["errors"][0]
    assert get_active_theme() is None


def test_activate_the_site_theme_with_nothing_new(client, django_user_model, theme):
    publish(theme)
    activate(theme)
    login(client, django_user_model, "change_theme", "publish_theme")
    reply = post(client, "publish", theme, {"activate": True}).json()
    assert (reply["published"], reply["activated"]) == (None, True)
    assert reply["state"]["is_default"] is True and theme.revisions.count() == 1


def test_publish_for_a_missing_theme_is_not_found(client, django_user_model):
    login(client, django_user_model, "change_theme", "publish_theme")
    response = client.post(
        reverse("capy_theme:editor_publish", args=[999]), "{}", content_type="application/json"
    )
    assert response.status_code == 404


def test_the_not_published_message_is_built_not_copied_from_the_error(
    client, django_user_model, monkeypatch
):
    # CodeQL: don't send an exception's text to the browser. The message is built
    # from the theme instead, so whatever the error says can't reach the user.
    from capy_theme.themes.active import NotPublished

    def refuse(*args, **kwargs):
        raise NotPublished("internal detail: /srv/app/secret.py line 3")

    monkeypatch.setattr("capy_theme.editor.views.publish_and_activate", refuse)
    login(client, django_user_model, "change_theme", "publish_theme")
    theme = Theme.objects.create(name="Main", slug="main")
    reply = post(client, "publish", theme, {"activate": True})
    assert reply.status_code == 400
    assert reply.json()["errors"] == ["Publish “Main” before activating it."]
