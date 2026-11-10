"""Tests for theme scheduling (issue #48)."""

from datetime import UTC, datetime, timedelta

import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.urls import reverse

from capy_theme.active import activate, get_active_theme, scheduled_assignments
from capy_theme.models import ScheduledTheme, Theme, ThemeAssignment
from capy_theme.publishing import publish

pytestmark = pytest.mark.django_db

DEC_1 = datetime(2026, 12, 1, tzinfo=UTC)
DEC_26 = datetime(2026, 12, 26, tzinfo=UTC)


class Clock:
    """A frozen clock: tests set .now and timezone.now() returns it."""

    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now


@pytest.fixture
def clock(monkeypatch):
    frozen = Clock(datetime(2026, 11, 15, tzinfo=UTC))
    monkeypatch.setattr("django.utils.timezone.now", frozen)
    cache.clear()
    yield frozen
    cache.clear()


def published(name):
    theme = Theme.objects.create(name=name, slug=name.lower())
    publish(theme)
    return theme


@pytest.fixture
def themes(clock):
    default = published("Default")
    activate(default)
    holiday = published("Holiday")
    ThemeAssignment.objects.create(theme=holiday, starts_at=DEC_1, ends_at=DEC_26)
    return default, holiday


def test_the_issue_check_holiday_theme_only_inside_its_dates(themes, clock):
    default, holiday = themes
    assert get_active_theme() == default  # 15 November
    clock.now = DEC_1 - timedelta(seconds=1)
    assert get_active_theme() == default
    clock.now = DEC_1  # the start is included
    assert get_active_theme() == holiday
    clock.now = datetime(2026, 12, 20, tzinfo=UTC)
    assert get_active_theme() == holiday
    clock.now = DEC_26  # the end isn't
    assert get_active_theme() == default


def test_the_cache_never_outlives_a_schedule_boundary(themes, clock, settings):
    default, holiday = themes
    settings.CAPY_THEME_CACHE_SECONDS = 60 * 60 * 24 * 365  # a very long cache
    assert get_active_theme() == default
    clock.now = DEC_1  # nothing cleared the cache, but its state expired
    assert get_active_theme() == holiday


def test_overlapping_schedules_the_latest_start_wins(themes, clock):
    _, holiday = themes
    sale = published("Sale")
    ThemeAssignment.objects.create(
        theme=sale, starts_at=datetime(2026, 12, 10, tzinfo=UTC), ends_at=DEC_26
    )
    clock.now = datetime(2026, 12, 5, tzinfo=UTC)
    assert get_active_theme() == holiday
    clock.now = datetime(2026, 12, 12, tzinfo=UTC)
    assert get_active_theme() == sale


def test_open_ended_schedules(themes, clock):
    default, _ = themes
    launch = published("Launch")
    ThemeAssignment.objects.create(theme=launch, starts_at=datetime(2027, 1, 1, tzinfo=UTC))
    clock.now = datetime(2030, 1, 1, tzinfo=UTC)
    assert get_active_theme() == launch
    old = published("Old")
    ThemeAssignment.objects.create(theme=old, ends_at=datetime(2026, 1, 1, tzinfo=UTC))
    assert get_active_theme() == launch  # the ended one doesn't come back


def test_a_visitors_choice_still_wins(themes, clock, rf):
    from capy_theme.active import CHOICE_COOKIE

    ocean = published("Ocean")
    ocean.offered_to_visitors = True
    ocean.save()
    clock.now = DEC_1
    request = rf.get("/")
    request.COOKIES[CHOICE_COOKIE] = "ocean"
    assert get_active_theme(request) == ocean


def test_scheduled_assignments_list(themes):
    _, holiday = themes
    assert [a.theme for a in scheduled_assignments()] == [holiday]


def test_validation(clock):
    theme = published("A")
    with pytest.raises(ValidationError, match="end must be after"):
        ThemeAssignment(theme=theme, starts_at=DEC_26, ends_at=DEC_1).full_clean()
    draft = Theme.objects.create(name="Draft", slug="draft")
    with pytest.raises(ValidationError, match="Publish this theme"):
        ThemeAssignment(theme=draft, starts_at=DEC_1).full_clean()


# The admin


@pytest.fixture
def admin_client(client, django_user_model):
    client.force_login(django_user_model.objects.create_superuser("s", "s@e.com", "pw"))
    return client


def test_admin_schedules_a_theme(themes, admin_client):
    default, holiday = themes
    url = reverse("admin:capy_theme_scheduledtheme_add")
    response = admin_client.post(
        url,
        {
            "theme": str(holiday.pk),
            "starts_at_0": "2027-03-01",
            "starts_at_1": "00:00:00",
            "ends_at_0": "2027-03-02",
            "ends_at_1": "00:00:00",
        },
    )
    assert response.status_code == 302, response.content.decode()[:2000]
    assert ScheduledTheme.objects.filter(theme=holiday).count() == 2
    listing = admin_client.get(reverse("admin:capy_theme_scheduledtheme_changelist"))
    content = listing.content.decode()
    assert "Upcoming" in content
    assert "(default)" not in content  # the default assignment isn't listed


def test_admin_needs_a_date(themes, admin_client):
    _, holiday = themes
    response = admin_client.post(
        reverse("admin:capy_theme_scheduledtheme_add"), {"theme": str(holiday.pk)}
    )
    assert response.status_code == 200
    assert "Give a start or an end date" in response.content.decode()


def test_admin_offers_only_published_themes(themes, admin_client):
    Theme.objects.create(name="Unpublished", slug="unpublished")
    content = admin_client.get(reverse("admin:capy_theme_scheduledtheme_add")).content
    assert b"Unpublished" not in content and b"Holiday" in content


def test_scheduling_needs_publish_permission(themes, client, django_user_model):
    from django.contrib.auth.models import Permission

    user = django_user_model.objects.create_user("e", password="pw", is_staff=True)
    user.user_permissions.add(Permission.objects.get(codename="change_theme"))
    user.user_permissions.add(Permission.objects.get(codename="view_theme"))
    client.force_login(user)
    assert client.get(reverse("admin:capy_theme_scheduledtheme_changelist")).status_code == 200
    assert client.get(reverse("admin:capy_theme_scheduledtheme_add")).status_code == 403
