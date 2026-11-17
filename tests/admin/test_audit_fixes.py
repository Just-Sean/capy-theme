"""Fixes from the final pre-v1 security audit (#275)."""

import pytest
from django.contrib.auth.models import Permission
from django.urls import reverse

from capy_theme.models import Theme
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin(client, django_user_model):
    client.force_login(django_user_model.objects.create_superuser("s", "s@e.com", "pw"))
    return client


# Malformed ids: Django's "doesn't exist" handling, not a server error


@pytest.mark.parametrize(
    "path",
    [
        "/admin/capy_theme/theme/{id}/revisions/",
        "/admin/capy_theme/theme/{id}/revisions/1/restore/",
        "/admin/capy_theme/theme/{id}/export/",
    ],
)
@pytest.mark.parametrize("bad", ["abc", "1.0", "-1", "99999"])
def test_a_malformed_or_missing_id_is_not_found(admin, path, bad):
    admin.raise_request_exception = False
    assert admin.get(path.format(id=bad)).status_code == 404


def test_the_pages_still_work_for_a_real_theme(admin):
    theme = Theme.objects.create(name="Main", slug="main")
    publish(theme)
    base = f"/admin/capy_theme/theme/{theme.pk}"
    assert admin.get(f"{base}/revisions/").status_code == 200
    assert admin.get(f"{base}/revisions/1/restore/").status_code == 200
    export = admin.get(f"{base}/export/")
    assert export.status_code == 200 and export["Content-Type"] == "application/zip"


def test_the_pages_still_need_their_permissions(client, django_user_model):
    theme = Theme.objects.create(name="Main", slug="main")
    publish(theme)
    user = django_user_model.objects.create_user("v", password="pw", is_staff=True)
    user.user_permissions.set(Permission.objects.filter(codename="view_theme"))
    client.force_login(user)
    base = f"/admin/capy_theme/theme/{theme.pk}"
    assert client.get(f"{base}/revisions/").status_code == 200  # viewing is enough
    assert client.get(f"{base}/revisions/1/restore/").status_code == 403  # needs publishing


# The draft custom CSS: the same people as every editor address


@pytest.fixture
def theme():
    return Theme.objects.create(
        name="Main", slug="main", settings={"custom_css": {"css": ".x{}", "enabled": True}}
    )


def user_with(django_user_model, *codenames, staff=True, active=True):
    user = django_user_model.objects.create_user(
        "u", password="pw", is_staff=staff, is_active=active
    )
    user.user_permissions.set(Permission.objects.filter(codename__in=codenames))
    return user


@pytest.mark.parametrize(
    ("codenames", "staff", "allowed"),
    [
        (["change_theme", "edit_custom_css"], True, True),
        (["edit_custom_css"], True, False),  # can't edit themes
        (["change_theme", "edit_custom_css"], False, False),  # not staff
        (["change_theme"], True, False),  # can't edit custom CSS
    ],
)
def test_the_draft_custom_css_is_only_for_editors(
    client, django_user_model, theme, codenames, staff, allowed
):
    client.force_login(user_with(django_user_model, *codenames, staff=staff))
    response = client.get(reverse("capy_theme:editor_custom_css", args=[theme.pk]))
    assert (response.status_code == 200) is allowed
    if allowed:
        assert response.content == b".x{}"
    else:
        assert response.status_code == 403
