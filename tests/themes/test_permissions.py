"""Tests for theme permissions (issue #12)."""

import pytest
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.urls import reverse

from capy_theme.models import Theme, ThemeRevision
from capy_theme.themes.active import get_active_theme
from capy_theme.themes.publishing import publish

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


def row_url(theme, action):
    return reverse(f"admin:capy_theme_theme_{action}", args=[theme.pk])


ROW_ACTIONS = ("publish_now", "publish_activate", "activate")


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


def draft_post(**extra):
    return {
        "name": "Main",
        "slug": "main",
        "light_base": "light",
        "dark_base": "dark",
        "assets-TOTAL_FORMS": "0",
        "assets-INITIAL_FORMS": "0",
        "revisions-TOTAL_FORMS": "0",
        "revisions-INITIAL_FORMS": "0",
        "revisions-MIN_NUM_FORMS": "0",
        "revisions-MAX_NUM_FORMS": "1000",
        **extra,
    }


def test_designer_cant_offer_a_theme_to_visitors(designer, theme):
    """Offering a theme puts it in front of visitors, so it needs publish_theme (#238)."""
    publish(theme)
    page = designer.get(change_url(theme)).content.decode()
    assert 'name="offered_to_visitors"' not in page
    response = designer.post(change_url(theme), draft_post(offered_to_visitors="on"))
    assert response.status_code == 302, response.content
    theme.refresh_from_db()
    assert theme.offered_to_visitors is False


def test_publisher_can_offer_a_theme_to_visitors(publisher, theme):
    publish(theme)
    response = publisher.post(change_url(theme), draft_post(offered_to_visitors="on"))
    assert response.status_code == 302, response.content
    theme.refresh_from_db()
    assert theme.offered_to_visitors is True


def test_designer_sees_only_save_draft(designer, theme):
    content = designer.get(change_url(theme)).content.decode()
    assert 'name="_capy_save"' in content
    assert 'name="_capy_publish"' not in content and 'name="_capy_publish_activate"' not in content
    assert "You can save drafts. To publish, ask someone who can publish themes" in content


def test_designer_direct_publish_requests_are_refused(designer, theme):
    for action in ROW_ACTIONS:
        assert designer.post(row_url(theme, action)).status_code == 403
    assert not ThemeRevision.objects.exists()


def test_designer_pressing_publish_only_saves_the_draft(designer, theme):
    response = designer.post(change_url(theme), draft_post(_capy_publish=""), follow=True)
    assert "The draft was saved, but you can&#x27;t publish themes." in response.content.decode()
    assert not ThemeRevision.objects.exists()


def test_designer_sees_no_row_buttons(designer, theme):
    content = designer.get(CHANGELIST).content.decode()
    assert "publish-now" not in content and "activate_theme" not in content


def test_designer_direct_activate_request_is_refused(designer, theme):
    publish(theme)
    assert designer.post(row_url(theme, "activate")).status_code == 403
    assert get_active_theme() is None


# A publisher can.


def test_publisher_sees_the_publish_buttons_and_can_publish(publisher, theme):
    content = publisher.get(change_url(theme)).content.decode()
    assert 'name="_capy_publish"' in content and 'name="_capy_publish_activate"' in content
    response = publisher.post(change_url(theme), draft_post(_capy_publish=""))
    assert response.status_code == 302, response.content
    theme.refresh_from_db()
    assert theme.live_revision is not None


def test_publisher_can_activate(publisher, theme):
    publish(theme)
    assert row_url(theme, "activate") in publisher.get(CHANGELIST).content.decode()
    publisher.post(row_url(theme, "activate"))
    assert get_active_theme() == theme


def test_superusers_can_publish(client, django_user_model, theme):
    client.force_login(django_user_model.objects.create_superuser("root", "r@example.com", "pw"))
    assert 'name="_capy_publish"' in client.get(change_url(theme)).content.decode()
