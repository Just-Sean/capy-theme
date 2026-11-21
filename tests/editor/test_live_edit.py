"""The live edit page at /theme/live-edit/ (issue #229): capy-theme's own page for
building a theme, the same in every project."""

import re
from pathlib import Path

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import override_settings

from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
URL = "/theme/live-edit/"
SRC = Path(__file__).resolve().parents[2] / "src/capy_theme"
STATIC = SRC / "static/capy_theme/editor"
TEMPLATES = SRC / "templates/capy_theme"


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def active():
    theme = Theme.objects.create(
        name="Main", slug="main", settings={"site_name": "Capy Co", "tagline": "Soft and calm"}
    )
    publish(theme)
    activate(theme)
    return theme


def log_in(client, django_user_model, *codenames, staff=True):
    user = django_user_model.objects.create_user("u", password="pw", is_staff=staff)
    user.user_permissions.set(
        Permission.objects.filter(content_type__app_label="capy_theme", codename__in=codenames)
    )
    client.force_login(user)


def test_visitors_are_sent_to_the_admin_login(client, active):
    response = client.get(URL)
    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/?next=/theme/live-edit/")


@pytest.mark.parametrize("codenames", [(), ("view_theme",)])
def test_staff_who_cant_edit_themes_are_refused(client, django_user_model, active, codenames):
    log_in(client, django_user_model, *codenames)
    assert client.get(URL).status_code == 403


def test_non_staff_are_refused_even_with_the_permission(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme", staff=False)
    assert client.get(URL).status_code == 403


def test_refusal_uses_the_projects_403_page(client, django_user_model, active, settings):
    # PermissionDenied, so the project's own 403 template is shown, not plain text.
    settings.DEBUG = False
    log_in(client, django_user_model, "view_theme")
    response = client.get(URL)
    assert response.status_code == 403
    assert response.content.decode() != "You can't edit themes."


def test_inactive_staff_are_refused(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme")
    django_user_model.objects.filter(username="u").update(is_active=False)
    # An inactive user's session no longer counts as logged in, so: the login page.
    response = client.get(URL)
    assert response.status_code == 302
    assert response["Location"].startswith("/admin/login/")


def test_the_page_cant_be_framed(client, django_user_model, active):
    # Its own header, even in a project without XFrameOptionsMiddleware (as here), so
    # another site can't frame the editor and trick a click on Save or Publish.
    log_in(client, django_user_model, "change_theme")
    assert client.get(f"{URL}?edit={active.pk}")["X-Frame-Options"] == "DENY"


@pytest.mark.parametrize("value", ["abc", "²", "-1", "1.0", ""])
def test_an_unreadable_edit_value_opens_the_active_theme(client, django_user_model, active, value):
    # "²" passes str.isdigit() but not int(): it used to crash the page.
    log_in(client, django_user_model, "change_theme")
    response = client.get(URL, {"edit": value})
    assert response.status_code == 302
    assert response["Location"] == f"{URL}?edit={active.pk}"


def test_a_theme_that_doesnt_exist_says_so(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme")
    response = client.get(f"{URL}?edit=99999")
    assert response.status_code == 200
    html = response.content.decode()
    assert "That theme doesn't exist" in html
    assert 'href="/admin/capy_theme/theme/"' in html
    assert 'id="capy-editor"' not in html


def test_an_unreadable_edit_value_with_no_themes_says_to_add_one(client, django_user_model):
    log_in(client, django_user_model, "change_theme")
    html = client.get(URL, {"edit": "abc"}).content.decode()
    assert "There's no theme to edit yet." in html


def test_without_edit_it_opens_on_the_active_theme(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme")
    response = client.get(URL)
    assert response.status_code == 302
    assert response["Location"] == f"{URL}?edit={active.pk}"


def test_without_an_active_theme_it_opens_on_the_first_theme(client, django_user_model):
    first = Theme.objects.create(name="First", slug="first")
    Theme.objects.create(name="Second", slug="second")
    log_in(client, django_user_model, "change_theme")
    assert client.get(URL)["Location"] == f"{URL}?edit={first.pk}"


def test_with_no_themes_it_says_to_add_one(client, django_user_model):
    log_in(client, django_user_model, "change_theme")
    response = client.get(URL)
    assert response.status_code == 200
    html = response.content.decode()
    assert "There's no theme to edit yet." in html
    assert 'href="/admin/capy_theme/theme/add/"' in html
    assert "capy-editor" not in html


def test_the_page_has_the_header_components_and_the_editor(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme")
    response = client.get(f"{URL}?edit={active.pk}")
    assert response.status_code == 200
    assert response["Cache-Control"].startswith("max-age=0")
    html = response.content.decode()
    # Its own bundled daisyUI stylesheet, then the theme's (from {% theme_head %}).
    assert "capy_theme/editor/components.css" in html
    assert html.index("capy_theme/editor/components.css") < html.index('id="capy-editor"')
    # The header: site name, tagline, Light / Dark / Auto, a link to the admin.
    assert "Capy Co" in html and "Soft and calm" in html
    for mode in ("Light", "Dark", "Auto"):
        assert f">{mode}<" in html
    assert 'href="/admin/"' in html
    # Every component, and the editor on the requested theme.
    for heading in ("Buttons", "Badges", "Card", "Alerts", "Table", "Form fields", "Headings"):
        assert f">{heading}</h2>" in html
    assert f'data-theme-id="{active.pk}"' in html
    assert "There's no theme to edit yet." not in html
    # The page's own heading and title name the theme being edited; a skip link.
    assert '<h1 class="sr-only">Live edit: Main</h1>' in html
    assert "<title>Live edit: Main</title>" in html
    assert 'href="#live-edit-main"' in html and 'id="live-edit-main"' in html


def test_the_title_names_the_theme_being_edited_not_the_active_one(
    client, django_user_model, active
):
    other = Theme.objects.create(name="Holiday", slug="holiday")
    log_in(client, django_user_model, "change_theme")
    html = client.get(f"{URL}?edit={other.pk}").content.decode()
    assert "<title>Live edit: Holiday</title>" in html
    assert f'data-theme-id="{other.pk}"' in html


def test_sample_headings_take_the_themes_heading_scale(client, django_user_model, active):
    # Utility classes would win over the theme's heading rules (they're in @layer
    # base), so the sample headings have none.
    log_in(client, django_user_model, "change_theme")
    html = client.get(f"{URL}?edit={active.pk}").content.decode()
    for level in range(1, 7):
        assert f"<h{level}>Heading {level}</h{level}>" in html


def test_sample_alerts_arent_announced_on_load(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme")
    html = client.get(f"{URL}?edit={active.pk}").content.decode()
    assert 'role="alert"' not in html


@override_settings(
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "APP_DIRS": True,
            "OPTIONS": {"context_processors": []},
        }
    ]
)
def test_the_page_doesnt_need_the_projects_context_processors(client, django_user_model, active):
    # A project without capy-theme's (or Django's request) context processor still
    # gets the full page: the view supplies `theme` and `request` itself.
    log_in(client, django_user_model, "change_theme")
    html = client.get(f"{URL}?edit={active.pk}").content.decode()
    assert "Capy Co" in html and ">Dark<" in html and 'id="capy-editor"' in html


def test_the_preview_toggle_is_internal_not_the_public_tags(client, django_user_model, active):
    # The editor is self-contained: its own preview toggle + script, and none of the
    # public switching tags' output, so stripping those tags (v2) doesn't touch it.
    log_in(client, django_user_model, "change_theme")
    html = client.get(f"{URL}?edit={active.pk}").content.decode()
    assert "data-capy-preview-mode=" in html
    assert "capy_theme/editor/mode-preview.js" in html
    # No output from {% theme_mode_toggle %} / {% theme_picker %} / the public head script.
    assert "/theme/mode/" not in html
    assert 'data-capy-mode="' not in html
    assert "/theme/choose/" not in html
    # It still links the editing theme's own stylesheet and mounts the editor.
    from capy_theme.css.stylesheet import stylesheet_url

    assert stylesheet_url(active.live_revision) in html
    assert 'id="capy-editor"' in html


def test_the_page_has_nothing_a_strict_csp_would_block(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme")
    html = client.get(f"{URL}?edit={active.pk}").content.decode()
    assert " style=" not in html
    assert " onclick=" not in html and " onsubmit=" not in html
    assert "<form" not in html  # Enter in a sample field must never reload the page


def test_only_get(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme")
    assert client.post(URL).status_code == 405


def test_switch_theme_lists_every_theme_and_opens_the_editor_on_it(
    client, django_user_model, active
):
    # Not the visitors' theme picker: it switches the theme being edited (#269).
    draft = Theme.objects.create(name="Autumn <draft>", slug="autumn", offered_to_visitors=False)
    log_in(client, django_user_model, "change_theme")
    html = " ".join(client.get(f"{URL}?edit={active.pk}").content.decode().split())
    assert ">Switch theme</summary>" in html
    assert "/theme/choose/" not in html
    assert (
        f'<a href="{URL}?edit={active.pk}" data-capy-edit-switch="Main" class="menu-active"'
        ' aria-current="page" >Main</a>'
    ) in html
    assert (
        f'<a href="{URL}?edit={draft.pk}" data-capy-edit-switch="Autumn &lt;draft&gt;" >'
        "Autumn &lt;draft&gt; (not published)</a>"
    ) in html
    assert html.index("Autumn &lt;draft&gt; (not") < html.index(">Main</a>")  # by name


def test_the_switch_theme_menus_classes_are_in_the_bundled_stylesheet():
    # The page's stylesheet only has the classes its build found, so a class added to
    # the template without rebuilding it does nothing (#269).
    template = (TEMPLATES / "editor/live_edit.html").read_text()
    menu = template[template.index('<details class="dropdown') : template.index("</details>")]
    classes = set()
    for value in re.findall(r'class="([^"]+)"', menu):
        classes.update(value.split())
    css = (STATIC / "components.css").read_text()
    for name in classes:
        selector = "." + re.sub(r"([\[\]])", r"\\\1", name)
        assert selector + "{" in css or selector + ":" in css or selector + "," in css, name


def test_switching_with_unsaved_changes_asks_first():
    script = (STATIC / "editor.js").read_text()
    handler = script[script.index('closest("[data-capy-edit-switch]")') :]
    assert "editor.isDirty()" in handler and "window.confirm(" in handler
    assert "event.preventDefault();" in handler  # Cancel stays on the page
    assert "event.altKey" in handler  # a download doesn't leave the page
    assert 'link.getAttribute("aria-current") === "page"' in handler  # a reload: browser warns
    # After a yes, the browser's own "leave site?" warning skips just that one time.
    assert "if (switching) {\n      switching = false;" in script
