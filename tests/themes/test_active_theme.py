"""Tests for active theme selection (issue #7)."""

import pytest
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.urls import reverse

from capy_theme.models import Theme, ThemeAssignment
from capy_theme.themes import active
from capy_theme.themes.active import NotPublished, activate, get_active_theme
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def empty_cache():
    cache.clear()
    yield
    cache.clear()


def published_theme(name, **kwargs):
    theme = Theme.objects.create(name=name, slug=name.lower(), **kwargs)
    publish(theme)
    return theme


def test_no_active_theme_by_default():
    assert get_active_theme() is None


def test_activating_changes_the_active_theme():
    first = published_theme("First")
    second = published_theme("Second")
    activate(first)
    assert get_active_theme() == first
    activate(second)
    assert get_active_theme() == second
    assert ThemeAssignment.objects.count() == 1  # one default assignment, switched


def test_active_theme_comes_with_its_live_revision():
    theme = published_theme("Main", light_base="cupcake")
    activate(theme)
    assert get_active_theme().live_revision.snapshot["light_base"] == "cupcake"


def test_second_call_makes_no_database_queries(django_assert_num_queries):
    activate(published_theme("Main"))
    get_active_theme()
    with django_assert_num_queries(0):
        theme = get_active_theme()
        assert theme.live_revision.number == 1  # loaded with it, no extra query


def test_no_active_theme_is_cached_too(django_assert_num_queries):
    get_active_theme()
    with django_assert_num_queries(0):
        assert get_active_theme() is None


def test_unpublished_theme_cant_be_activated():
    theme = Theme.objects.create(name="Draft", slug="draft")
    with pytest.raises(NotPublished):
        activate(theme)
    assert get_active_theme() is None


def test_publishing_clears_the_cache():
    theme = published_theme("Main")
    activate(theme)
    assert get_active_theme().live_revision.number == 1
    theme.light_base = "cupcake"
    theme.save()
    publish(theme)
    assert get_active_theme().live_revision.number == 2


def test_changing_the_assignment_clears_the_cache():
    first = published_theme("First")
    second = published_theme("Second")
    activate(first)
    get_active_theme()
    ThemeAssignment.objects.update_or_create(site="", defaults={"theme": second})
    assert get_active_theme() == second


def test_deleting_the_active_theme_leaves_none_active():
    theme = published_theme("Main")
    activate(theme)
    get_active_theme()
    theme.delete()
    assert get_active_theme() is None


def test_cache_time_defaults_to_5_minutes_and_follows_the_setting(settings, monkeypatch):
    timeouts = []
    monkeypatch.setattr(active.cache, "set", lambda key, value, timeout: timeouts.append(timeout))
    get_active_theme()
    settings.CAPY_THEME_CACHE_SECONDS = 60
    get_active_theme()
    assert timeouts == [300, 60]


def test_only_one_default_assignment_per_site():
    theme = published_theme("Main")
    ThemeAssignment.objects.create(theme=theme)
    with pytest.raises(IntegrityError), transaction.atomic():
        ThemeAssignment.objects.create(theme=theme)


def test_get_active_theme_accepts_a_request(rf):
    activate(published_theme("Main"))
    assert get_active_theme(rf.get("/")).name == "Main"


# The admin


@pytest.fixture
def admin(client, django_user_model):
    user = django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")
    client.force_login(user)
    return client


def run_activate(admin, *themes):
    return admin.post(
        reverse("admin:capy_theme_theme_changelist"),
        {"action": "activate_theme", "_selected_action": [t.pk for t in themes]},
        follow=True,
    )


def test_admin_activate_action(admin):
    theme = published_theme("Main")
    response = run_activate(admin, theme)
    assert "“Main” is now the active theme." in response.content.decode()
    assert get_active_theme() == theme


def test_admin_refuses_unpublished_theme(admin):
    theme = Theme.objects.create(name="Draft", slug="draft")
    response = run_activate(admin, theme)
    assert "Publish “Draft” before activating it." in response.content.decode()
    assert get_active_theme() is None


def test_admin_refuses_more_than_one_theme(admin):
    response = run_activate(admin, published_theme("One"), published_theme("Two"))
    assert "Select exactly one theme to activate." in response.content.decode()
    assert get_active_theme() is None


def test_admin_list_shows_which_theme_is_active(admin):
    activate(published_theme("Main"))
    response = admin.get(reverse("admin:capy_theme_theme_changelist"))
    assert b"Active" in response.content
    assert b"icon-yes.svg" in response.content
