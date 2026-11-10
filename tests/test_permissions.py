"""Tests for theme permissions (issue #12)."""

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.urls import reverse

from capy_theme.active import get_active_theme
from capy_theme.models import Theme, ThemeRevision
from capy_theme.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


def perms(*codenames):
    return Permission.objects.filter(content_type__app_label="capy_theme", codename__in=codenames)


def user_in_group(django_user_model, name, *codenames):
    group = Group.objects.create(name=name)
    group.permissions.set(perms(*codenames))
    user = django_user_model.objects.create_user(name.lower(), password="pw", is_staff=True)
    user.groups.add(group)
    return user


@pytest.fixture
def designer(client, django_user_model):
    """The issue's check: a "Designer" group with only view, add and change."""
    user = user_in_group(django_user_model, "Designer", "view_theme", "add_theme", "change_theme")
    client.force_login(user)
    return client


@pytest.fixture
def publisher(client, django_user_model):
    user = user_in_group(
        django_user_model, "Publisher", "view_theme", "change_theme", "publish_theme"
    )
    client.force_login(user)
    return client


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


def change_url(theme):
    return reverse("admin:capy_theme_theme_change", args=[theme.pk])


def publish_url(theme):
    return reverse("admin:capy_theme_theme_publish", args=[theme.pk])


CHANGELIST = reverse("admin:capy_theme_theme_changelist")


def test_permissions_are_declared():
    assert set(
        perms("publish_theme", "edit_custom_css", "import_theme").values_list("codename", flat=True)
    ) == {
        "publish_theme",
        "edit_custom_css",
        "import_theme",
    }


# A designer can edit drafts but not publish or activate.


def test_designer_can_edit_drafts(designer, theme):
    response = designer.post(
        change_url(theme),
        {
            "name": "Main",
            "slug": "main",
            "light_base": "cupcake",
            "dark_base": "dark",
            "assets-TOTAL_FORMS": "0",
            "assets-INITIAL_FORMS": "0",
            "revisions-TOTAL_FORMS": "0",
            "revisions-INITIAL_FORMS": "0",
            "revisions-MIN_NUM_FORMS": "0",
            "revisions-MAX_NUM_FORMS": "1000",
        },
    )
    assert response.status_code == 302, response.content
    theme.refresh_from_db()
    assert theme.light_base == "cupcake"


def test_designer_sees_no_publish_button(designer, theme):
    content = designer.get(change_url(theme)).content.decode()
    assert publish_url(theme) not in content


def test_designer_direct_publish_request_is_refused(designer, theme):
    assert designer.get(publish_url(theme)).status_code == 403
    assert designer.post(publish_url(theme), {"note": ""}).status_code == 403
    assert not ThemeRevision.objects.exists()


def test_designer_sees_no_activate_action(designer, theme):
    content = designer.get(CHANGELIST).content.decode()
    assert "activate_theme" not in content


def test_designer_direct_activate_request_is_refused(designer, theme):
    publish(theme)
    designer.post(CHANGELIST, {"action": "activate_theme", "_selected_action": [theme.pk]})
    assert get_active_theme() is None


# A publisher can.


def test_publisher_sees_the_publish_button_and_can_publish(publisher, theme):
    assert publish_url(theme) in publisher.get(change_url(theme)).content.decode()
    response = publisher.post(publish_url(theme), {"note": ""})
    assert response.status_code == 302
    theme.refresh_from_db()
    assert theme.live_revision is not None


def test_publisher_can_activate(publisher, theme):
    publish(theme)
    assert "activate_theme" in publisher.get(CHANGELIST).content.decode()
    publisher.post(CHANGELIST, {"action": "activate_theme", "_selected_action": [theme.pk]})
    assert get_active_theme() == theme


def test_superusers_can_publish(client, django_user_model, theme):
    client.force_login(django_user_model.objects.create_superuser("root", "r@example.com", "pw"))
    assert publish_url(theme) in client.get(change_url(theme)).content.decode()
