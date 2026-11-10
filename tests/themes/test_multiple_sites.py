"""Tests for serving several domains, each with its own theme (issue #60)."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import Permission
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.template import Context, Template
from django.utils import timezone

from capy_theme.css.stylesheet import stylesheet_url
from capy_theme.models import SiteTheme, Theme, ThemeAssignment
from capy_theme.themes.active import activate, get_active_theme, site_of
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def hosts(settings):
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "shop.example.com", "testserver"]
    cache.clear()
    yield
    cache.clear()


def published(name, **fields):
    theme = Theme.objects.create(name=name, slug=name.lower(), **fields)
    publish(theme)
    return theme


@pytest.fixture
def themes():
    main = published("Main")
    other = published("Other", light_base="cupcake")
    activate(main)
    activate(other, site="127.0.0.1")
    return main, other


def on(rf, host):
    return rf.get("/", HTTP_HOST=host)


def test_the_issue_check_two_hostnames_show_different_themes(rf, themes):
    main, other = themes
    assert get_active_theme(on(rf, "localhost")) == main
    assert get_active_theme(on(rf, "127.0.0.1")) == other
    head = Template("{% load capy_theme %}{% theme_head %}")
    local = head.render(Context({"request": on(rf, "localhost:8000")}))
    ip = head.render(Context({"request": on(rf, "127.0.0.1:8000")}))
    assert stylesheet_url(main.live_revision) in local
    assert stylesheet_url(other.live_revision) in ip


def test_other_domains_and_no_request_use_the_theme_for_every_site(rf, themes):
    main, _ = themes
    assert get_active_theme(on(rf, "shop.example.com")) == main
    assert get_active_theme() == main


def test_port_and_case_dont_matter(rf, themes):
    _, other = themes
    assert site_of(on(rf, "127.0.0.1:8001")) == "127.0.0.1"
    SiteTheme.objects.filter(site="127.0.0.1").update(site="shop.example.com")
    cache.clear()
    assert get_active_theme(on(rf, "SHOP.example.com:443")) == other


def test_a_sites_schedule_wins_on_that_site(rf, themes):
    main, other = themes
    sale = published("Sale")
    now = timezone.now()
    ThemeAssignment.objects.create(
        theme=sale,
        site="localhost",
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
    )
    assert get_active_theme(on(rf, "localhost")) == sale
    assert get_active_theme(on(rf, "127.0.0.1")) == other
    assert get_active_theme(on(rf, "shop.example.com")) == main


def test_a_site_theme_wins_over_a_schedule_for_every_site(rf, themes):
    _, other = themes
    holiday = published("Holiday")
    now = timezone.now()
    ThemeAssignment.objects.create(theme=holiday, starts_at=now - timedelta(days=1))
    assert get_active_theme(on(rf, "127.0.0.1")) == other  # its own theme
    assert get_active_theme(on(rf, "localhost")) == holiday  # the schedule for every site


def test_changing_one_site_clears_every_sites_cache(rf, themes):
    main, other = themes
    assert get_active_theme(on(rf, "127.0.0.1")) == other
    activate(main, site="127.0.0.1")
    assert get_active_theme(on(rf, "127.0.0.1")) == main


@pytest.mark.parametrize(
    "bad", ["https://example.com", "example.com/shop", "example.com:8000", "a b"]
)
def test_only_bare_domains(themes, bad):
    main, _ = themes
    with pytest.raises(ValidationError, match="Just the domain"):
        ThemeAssignment(theme=main, site=bad).full_clean()


# The admin


def staff(client, django_user_model, *codenames):
    user = django_user_model.objects.create_user("s", password="pw", is_staff=True)
    for codename in codenames:
        user.user_permissions.add(Permission.objects.get(codename=codename))
    client.force_login(user)
    return client


def test_site_themes_admin(client, django_user_model, themes):
    main, other = themes
    staff(client, django_user_model, "view_theme", "publish_theme")
    listing = client.get("/admin/capy_theme/sitetheme/").content.decode()
    assert "127.0.0.1" in listing
    assert "Every site" not in listing  # the theme for every site isn't listed here
    response = client.post(
        "/admin/capy_theme/sitetheme/add/", {"site": " Shop.Example.com ", "theme": str(other.pk)}
    )
    assert response.status_code == 302
    assert SiteTheme.objects.filter(site="shop.example.com", theme=other).exists()


def test_site_themes_need_the_publish_permission(client, django_user_model, themes):
    staff(client, django_user_model, "view_theme", "change_theme")
    assert client.get("/admin/capy_theme/sitetheme/").status_code == 200
    assert client.get("/admin/capy_theme/sitetheme/add/").status_code == 403


def test_a_schedule_can_be_for_one_site(client, django_user_model, themes):
    main, _ = themes
    staff(client, django_user_model, "view_theme", "publish_theme")
    response = client.post(
        "/admin/capy_theme/scheduledtheme/add/",
        {
            "theme": str(main.pk),
            "site": "localhost",
            "starts_at_0": "2099-01-01",
            "starts_at_1": "00:00:00",
        },
    )
    assert response.status_code == 302
    assert ThemeAssignment.objects.get(starts_at__isnull=False).site == "localhost"
