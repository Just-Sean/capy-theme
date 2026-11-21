"""Tests for active theme selection (issue #7)."""

import pytest
from django.core.cache import cache
from django.db import IntegrityError, OperationalError, transaction
from django.urls import reverse

from capy_theme.models import Theme, ThemeAssignment
from capy_theme.themes import active
from capy_theme.themes.active import NotPublished, activate, primary_theme
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
    assert primary_theme() is None


def test_activating_changes_the_active_theme():
    first = published_theme("First")
    second = published_theme("Second")
    activate(first)
    assert primary_theme() == first
    activate(second)
    assert primary_theme() == second
    # One default light assignment, switched (both themes are light).
    assert ThemeAssignment.objects.count() == 1


def test_active_theme_comes_with_its_live_revision():
    theme = published_theme("Main", base="cupcake")
    activate(theme)
    assert primary_theme().live_revision.snapshot["base"] == "cupcake"


def test_second_call_makes_no_database_queries(django_assert_num_queries):
    activate(published_theme("Main"))
    primary_theme()
    with django_assert_num_queries(0):
        theme = primary_theme()
        assert theme.live_revision.number == 1  # loaded with it, no extra query


def test_no_active_theme_is_cached_too(django_assert_num_queries):
    primary_theme()
    with django_assert_num_queries(0):
        assert primary_theme() is None


def test_unpublished_theme_cant_be_activated():
    theme = Theme.objects.create(name="Draft", slug="draft")
    with pytest.raises(NotPublished):
        activate(theme)
    assert primary_theme() is None


def test_publishing_clears_the_cache():
    theme = published_theme("Main")
    activate(theme)
    assert primary_theme().live_revision.number == 1
    theme.base = "cupcake"
    theme.save()
    publish(theme)
    assert primary_theme().live_revision.number == 2


def test_changing_the_assignment_clears_the_cache():
    first = published_theme("First")
    second = published_theme("Second")
    activate(first)
    primary_theme()
    ThemeAssignment.objects.update_or_create(site="", defaults={"theme": second})
    assert primary_theme() == second


def test_deleting_the_active_theme_leaves_none_active():
    theme = published_theme("Main")
    activate(theme)
    primary_theme()
    theme.delete()
    assert primary_theme() is None


def test_cache_time_defaults_to_5_minutes_and_follows_the_setting(settings, monkeypatch):
    timeouts = []

    def record(key, value, timeout):
        if key != active.GENERATION_KEY:  # the generation marker never expires
            timeouts.append(timeout)

    monkeypatch.setattr(active.cache, "set", record)
    primary_theme()
    settings.CAPY_THEME_CACHE_SECONDS = 60
    primary_theme()
    assert timeouts == [300, 60]


def test_only_one_default_assignment_per_site_and_scheme():
    theme = published_theme("Main")
    ThemeAssignment.objects.create(theme=theme)  # scheme defaults to light
    with pytest.raises(IntegrityError), transaction.atomic():
        ThemeAssignment.objects.create(theme=theme)


def test_primary_theme_accepts_a_request(rf):
    activate(published_theme("Main"))
    assert primary_theme(rf.get("/")).name == "Main"


# The admin


@pytest.fixture
def admin(client, django_user_model):
    user = django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")
    client.force_login(user)
    return client


def run_activate(admin, theme):
    """The theme list's Activate button on the theme's row (#273)."""
    url = reverse("admin:capy_theme_theme_activate", args=[theme.pk])
    return admin.post(url, follow=True)


def test_admin_activate_button(admin):
    theme = published_theme("Main")
    response = run_activate(admin, theme)
    assert "“Main” is now the default light theme." in response.content.decode()
    assert primary_theme() == theme


def test_admin_refuses_unpublished_theme(admin):
    theme = Theme.objects.create(name="Draft", slug="draft")
    response = run_activate(admin, theme)
    assert "Publish “Draft” before activating it." in response.content.decode()
    assert primary_theme() is None


def test_admin_list_shows_which_theme_is_active(admin):
    activate(published_theme("Main"))
    response = admin.get(reverse("admin:capy_theme_theme_changelist"))
    assert b"Showing now" in response.content  # the column (#273: was "Active")
    assert b"icon-yes.svg" in response.content


# Resilience when the cache or database is unreachable (issue #278).


class _BrokenCache:
    """A cache whose every read and write raises, to stand in for the backend being down."""

    def get(self, *args, **kwargs):
        raise RuntimeError("cache down")

    def set(self, *args, **kwargs):
        raise RuntimeError("cache down")


def test_a_cache_outage_falls_back_to_the_database(monkeypatch):
    theme = published_theme("Main")
    activate(theme)
    monkeypatch.setattr(active, "cache", _BrokenCache())
    assert primary_theme() == theme  # served from the database instead of 500ing


def test_saving_a_theme_works_when_the_cache_is_down(monkeypatch):
    monkeypatch.setattr(active, "cache", _BrokenCache())
    # Saving fires the signal that calls clear_cache(), which writes to the cache.
    theme = published_theme("Main")  # creating and publishing must not raise
    activate(theme)  # activating calls clear_cache(); must not raise
    assert Theme.objects.filter(slug="main").exists()


def test_a_database_outage_serves_no_theme_instead_of_erroring(monkeypatch):
    activate(published_theme("Main"))
    cache.clear()  # force the database path

    def boom(*args, **kwargs):
        raise OperationalError("database down")

    monkeypatch.setattr(active, "_assignments", boom)
    assert primary_theme() is None  # no theme, but no 500 either


class _CorruptCache:
    """Returns a wrong-shape value for the state key (e.g. a cache shared across
    deployments or versions), to check a bad entry is treated as a miss, not a crash."""

    def __init__(self, value):
        self.value = value

    def get(self, key, default=None):
        return "gen" if key == active.GENERATION_KEY else self.value

    def set(self, *args, **kwargs):
        pass


@pytest.mark.parametrize("bad", [{"theme": None}, "not-a-dict", 42, []])
def test_a_malformed_cached_value_is_treated_as_a_miss(monkeypatch, bad):
    theme = published_theme("Main")
    activate(theme)
    monkeypatch.setattr(active, "cache", _CorruptCache(bad))
    assert primary_theme() == theme  # fell through to the database, no 500
