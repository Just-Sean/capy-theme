"""Tests for the editor's colour and shape controls (issue #97).

The controls themselves are JavaScript (editor/controls/*.js), checked in headless
Chrome while building. These tests cover the data the server gives them.
"""

from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from capy_theme.colors.names import COLOR_NAMES
from capy_theme.editor.preview import preview
from capy_theme.editor.state import controls
from capy_theme.models import Theme

pytestmark = pytest.mark.django_db
STATIC = Path(__file__).resolve().parents[2] / "src/capy_theme/static/capy_theme/editor"


@pytest.fixture
def editor_client(client, django_user_model):
    user = django_user_model.objects.create_user("staff", password="pw", is_staff=True)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename="change_theme")
    )
    client.force_login(user)
    return client


def test_controls_list_bases_colours_and_shape():
    spec = controls()
    assert "cupcake" in spec["bases"]["light"] and "cupcake" not in spec["bases"]["dark"]
    assert [g["name"] for g in spec["color_groups"]] == ["Basic", "Advanced", "Expert"]
    assert sum(len(g["colors"]) for g in spec["color_groups"]) == 20
    assert {s["name"] for s in spec["sizes"]} >= {"radius_box", "border"}
    assert {e["name"] for e in spec["effects"]} == {"depth", "noise"}


def test_bases_follow_the_project_setting(settings):
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]
    assert controls()["bases"] == {"light": ["light"], "dark": ["dark"]}


def test_preview_gives_hex_for_every_colour_picker():
    theme = Theme.objects.create(name="Main", slug="main")
    result = preview(theme, {"settings": {"colors": {"light": {"primary": "#16a34a"}}}})
    assert set(result["hex"]["light"]) == set(COLOR_NAMES)
    assert result["hex"]["light"]["primary"] == "#16a34a"
    assert result["light_base"] == "light"


def test_state_includes_controls_and_current_values(editor_client):
    theme = Theme.objects.create(name="Main", slug="main", settings={"shape": {"radius_box": 0}})
    data = editor_client.get(reverse("capy_theme:editor_state", args=[theme.pk])).json()
    assert data["controls"]["color_groups"][0]["colors"][0] == {
        "name": "primary",
        "label": "Primary",
    }
    assert data["values"]["light"]["--radius-box"] == "0rem"
    assert data["hex"]["dark"]["base-100"].startswith("#")
    assert len(data["contrast"]["light"]) == 11


def test_mount_loads_the_controls_script(editor_client):
    theme = Theme.objects.create(name="Main", slug="main")
    content = editor_client.get(f"/page/?edit={theme.pk}").content.decode()
    assert content.index("editor/editor.js") < content.index("editor/controls/core.js")
    assert content.index("editor/controls/core.js") < content.index("editor/controls/colors.js")


def test_controls_script_is_bundled():
    script = "".join(path.read_text() for path in sorted((STATIC / "controls").glob("*.js")))
    for marker in ("data-capy-picker", "data-capy-reset", "data-capy-shape", "schedulePreview"):
        assert marker in script


def test_the_page_makes_room_for_the_open_editor():
    # Issue #193: the panel and banner covered the page's own controls (e.g. the
    # Light / Dark / Auto buttons). Opening the editor marks <html>, and the page
    # then moves down by the banner's height and, on wide screens, left by the
    # panel's width. Checked in a browser too (see the PR).
    script = (STATIC / "editor.js").read_text()
    assert 'classList.add("capy-editor-open")' in script
    assert 'classList.remove("capy-editor-open")' in script
    css = (STATIC / "editor.css").read_text()
    assert "height: 2.5rem;" in css  # the banner
    assert "html.capy-editor-open body { margin-top: 2.5rem; }" in css
    assert "@media (min-width: 48rem)" in css
    assert "html.capy-editor-open body { margin-right: 24rem; }" in css
    assert "width: min(24rem, 100vw);" in css  # the panel
