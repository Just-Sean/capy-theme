"""Tests for who gets the live editor, which theme it edits, and its state (issue #42)."""

from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.urls import reverse

from capy_theme.editor.access import can_edit, can_publish
from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
PAGE = "/page/"  # an ordinary project page with {% theme_head %} (tests/urls.py)
PINK = "oklch(65% 0.24 350)"
STATIC = Path(__file__).resolve().parents[2] / "src/capy_theme/static/capy_theme/editor"


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


def staff_user(django_user_model, *codenames):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename__in=codenames)
    )
    return django_user_model.objects.get(pk=user.pk)  # fresh, so permissions aren't cached


@pytest.fixture
def editor_client(client, django_user_model):
    client.force_login(staff_user(django_user_model, "view_theme", "change_theme"))
    return client


@pytest.fixture
def active():
    theme = Theme.objects.create(name="Main", slug="main")
    publish(theme)
    activate(theme)
    return theme


def state_url(theme):
    return reverse("capy_theme:editor_state", args=[theme.pk])


# Who can edit


def test_staff_with_change_permission_can_edit(django_user_model):
    user = staff_user(django_user_model, "change_theme")
    assert can_edit(user)
    assert not can_publish(user)


def test_staff_without_change_permission_cant(django_user_model):
    assert not can_edit(staff_user(django_user_model, "view_theme"))


def test_editors_get_the_editor(editor_client, active):
    content = editor_client.get(PAGE).content.decode()
    assert 'id="capy-editor"' in content
    assert "capy_theme/editor/editor.js" in content
    assert f'data-state-url="{state_url(active)}"' in content


def test_no_editor_without_permission(client, django_user_model, active):
    client.force_login(staff_user(django_user_model, "view_theme"))
    content = client.get(PAGE).content.decode()
    assert 'id="capy-editor"' not in content
    assert "editor.js" not in content


def test_no_editor_without_a_theme(editor_client):
    assert 'id="capy-editor"' not in editor_client.get(PAGE).content.decode()


def test_edit_parameter_picks_another_theme(editor_client, active):
    other = Theme.objects.create(name="Other", slug="other")
    content = editor_client.get(f"{PAGE}?edit={other.pk}").content.decode()
    assert f'data-state-url="{state_url(other)}"' in content
    assert 'data-theme-name="Other"' in content


# The state endpoint


def test_state_has_the_draft_and_its_css(editor_client, active):
    active.settings = {"colors": {"light": {"primary": PINK}}}
    active.save()
    response = editor_client.get(state_url(active))
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    data = response.json()
    assert data["name"] == "Main"
    assert data["settings"]["colors"]["light"]["primary"] == PINK
    assert f"--color-primary: {PINK};" in data["css"]
    assert data["live_revision"] == 1
    assert data["has_unpublished_changes"] is True
    assert data["can_publish"] is False


def test_state_css_matches_publishing(editor_client, active):
    from capy_theme.css.stylesheet import render_css

    data = editor_client.get(state_url(active)).json()
    published = render_css(active.live_revision)
    # Same rules; only the comment line differs.
    assert data["css"].splitlines()[1:] == published.splitlines()[1:]


def test_state_is_refused_without_permission(client, django_user_model, active):
    client.force_login(staff_user(django_user_model, "view_theme"))
    assert client.get(state_url(active)).status_code == 403
    client.logout()
    assert client.get(state_url(active)).status_code == 403


def test_viewing_the_state_changes_nothing(editor_client, active):
    before = Theme.objects.get(pk=active.pk).updated_at
    editor_client.get(state_url(active))
    assert Theme.objects.get(pk=active.pk).updated_at == before


def test_visitors_dont_get_the_editor(client, settings, active):
    settings.CAPY_THEME_PAGE = "public"
    assert "editor.js" not in client.get(PAGE).content.decode()


# The bundled files


def test_editor_files_are_bundled():
    script = (STATIC / "editor.js").read_text()
    assert "adoptedStyleSheets" in script
    assert "data-capy-editor-open" in script
    assert ".capy-editor" in (STATIC / "editor.css").read_text()


# Keyboard focus (#245). The behavior itself runs in the browser; these check the
# script has each part, and that the width it uses matches the stylesheet's.


def test_editor_moves_focus_into_the_panel_and_back():
    script = (STATIC / "editor.js").read_text()
    assert '"aria-label": "Theme editor", tabindex: "-1"' in script
    assert "editor.panel.focus()" in script and "returnFocus()" in script


def test_escape_closes_the_editor():
    script = (STATIC / "editor.js").read_text()
    assert 'event.key !== "Escape"' in script and "editor.close()" in script


def test_escape_in_the_components_view_closes_only_the_view():
    # The editor's Escape handler ignores the view and steps aside while it's open (#251).
    script = (STATIC / "editor.js").read_text()
    assert 'closest(".capy-editor, .capy-editor-banner")' in script
    assert '.capy-editor-components:not([hidden])")) return;' in script


def test_page_behind_a_full_width_panel_is_inert():
    script = (STATIC / "editor.js").read_text()
    css = (STATIC / "editor.css").read_text()
    # The panel covers the page below 48rem, where the page stops making room.
    assert "@media (min-width: 48rem)" in css
    assert 'matchMedia("(max-width: 47.99rem)")' in script
    assert 'setAttribute("inert", "")' in script


def test_save_and_publish_keep_focus_on_their_button():
    script = (STATIC / "controls" / "actions.js").read_text()
    assert 'refocus("[data-capy-save]")' in script
    assert 'refocus("[data-capy-publish]")' in script


# "See it as a visitor" is gone; Revert goes back to the saved draft (#261).


def test_see_it_as_a_visitor_is_gone(editor_client, active):
    assert editor_client.get("/theme/editor/visitor-view/").status_code == 404
    state = editor_client.get(state_url(active)).json()
    assert "visitors" not in state and "visitor_view" not in state["urls"]
    page = editor_client.get(PAGE).content.decode()
    assert "visitor.js" not in page and "data-visitor-view-url" not in page
    assert not (STATIC / "controls" / "visitor.js").exists()


def test_revert_goes_back_to_the_saved_draft():
    actions = (STATIC / "controls" / "actions.js").read_text()
    core = (STATIC / "controls" / "core.js").read_text()
    script = (STATIC / "editor.js").read_text()
    revert_button = (
        '"data-capy-revert": "", "aria-describedby": "capy-editor-revert-note", text: "Revert"'
    )
    assert revert_button in actions
    assert 'id: "capy-editor-revert-note"' in actions
    # Revert keeps images uploaded since the last save.
    images = (STATIC / "controls" / "images.js").read_text()
    assert "ui.saved.assets = body.assets" in images
    assert "editor.isDirty()" in actions and "window.confirm(" in actions
    assert "ui.build(ui.saved)" in actions and "ui.saved = state;" in core
    # A preview still on its way can't put the discarded changes back.
    assert "editor.cancelPreview();" in actions
    assert "if (round !== previewRound) return result;" in script
