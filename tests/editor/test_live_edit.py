"""The live edit page at /theme/live-edit/ (issue #229): capy-theme's own page for
building a theme, the same in every project."""

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.test import override_settings

from capy_theme.models import Theme
from capy_theme.themes.active import activate
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db
URL = "/theme/live-edit/"


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


def test_the_page_has_nothing_a_strict_csp_would_block(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme")
    html = client.get(f"{URL}?edit={active.pk}").content.decode()
    assert " style=" not in html
    assert " onclick=" not in html and " onsubmit=" not in html
    assert "<form" not in html  # Enter in a sample field must never reload the page


def test_only_get(client, django_user_model, active):
    log_in(client, django_user_model, "change_theme")
    assert client.post(URL).status_code == 405
