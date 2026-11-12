"""Tests for the admin's Publish page and revision list (issue #12)."""

import pytest
from django.db import IntegrityError
from django.urls import reverse

from capy_theme.models import Theme, ThemeRevision
from capy_theme.themes.publishing import publish

pytestmark = pytest.mark.django_db


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")


@pytest.fixture
def admin(client, user):
    client.force_login(user)
    return client


def publish_url(theme):
    return reverse("admin:capy_theme_theme_publish", args=[theme.pk])


def change_url(theme):
    return reverse("admin:capy_theme_theme_change", args=[theme.pk])


def test_edit_page_has_publish_button_and_status(admin, theme):
    response = admin.get(change_url(theme))
    assert response.status_code == 200
    assert publish_url(theme).encode() in response.content
    assert b"Never published" in response.content


def test_publish_page_shows_confirmation_with_note(admin, theme):
    response = admin.get(publish_url(theme))
    assert response.status_code == 200
    assert b'name="note"' in response.content
    assert b"never been published" in response.content
    assert not ThemeRevision.objects.exists()  # opening the page doesn't publish


def test_publish_page_publishes_with_note(admin, theme, user):
    response = admin.post(publish_url(theme), {"note": "Launch"})
    assert response.status_code == 302
    assert response.url == change_url(theme)
    theme.refresh_from_db()
    assert theme.live_revision.number == 1
    assert theme.live_revision.note == "Launch"
    assert theme.live_revision.published_by == user


def test_publish_page_with_no_changes_says_so(admin, theme, user):
    publish(theme, user=user)
    response = admin.get(publish_url(theme))
    assert b"Nothing to publish" in response.content
    assert b'name="note"' not in response.content
    response = admin.post(publish_url(theme), {"note": ""}, follow=True)
    assert b"Nothing to publish" in response.content
    assert theme.revisions.count() == 1


def test_edit_page_lists_revisions_read_only(admin, theme, user):
    publish(theme, user=user, note="First")
    response = admin.get(change_url(theme))
    content = response.content.decode()
    assert "Published revisions" in content
    assert "First" in content
    assert "revisions-0-DELETE" not in content  # no delete checkbox
    assert 'name="revisions-0-note"' not in content  # not editable


def test_saving_the_edit_form_doesnt_publish(admin, theme, user):
    publish(theme, user=user)
    data = {
        "name": "Main",
        "slug": "main",
        "light_base": "cupcake",
        "dark_base": "dark",
        "settings": "{}",
        "assets-TOTAL_FORMS": "0",
        "assets-INITIAL_FORMS": "0",
        "revisions-TOTAL_FORMS": "1",
        "revisions-INITIAL_FORMS": "1",
        "revisions-MIN_NUM_FORMS": "0",
        "revisions-MAX_NUM_FORMS": "1000",
    }
    response = admin.post(change_url(theme), data)
    assert response.status_code == 302, response.content
    theme.refresh_from_db()
    assert theme.light_base == "cupcake"
    assert theme.live_revision.snapshot["light_base"] == "light"
    assert theme.has_unpublished_changes


def test_list_shows_live_revision_and_unpublished_changes(admin, theme, user):
    publish(theme, user=user)
    response = admin.get(reverse("admin:capy_theme_theme_changelist"))
    assert response.status_code == 200
    assert b"Live revision" in response.content
    assert b"Unpublished changes" in response.content


def test_publish_page_explains_a_simultaneous_publish(admin, theme, monkeypatch):
    # Simulates someone else publishing at the same moment: the database
    # refuses the duplicate revision number.
    def collide(*args, **kwargs):
        raise IntegrityError("duplicate revision number")

    monkeypatch.setattr("capy_theme.admin.publish_pages.publish", collide)
    response = admin.post(publish_url(theme), {"note": ""}, follow=True)
    assert response.status_code == 200
    assert b"Someone else just published this theme" in response.content
    assert not ThemeRevision.objects.exists()


def test_staff_without_change_permission_cant_publish(client, theme, django_user_model):
    viewer = django_user_model.objects.create_user("viewer", password="pw", is_staff=True)
    client.force_login(viewer)
    response = client.post(publish_url(theme), {"note": ""})
    assert response.status_code == 403
    assert not ThemeRevision.objects.exists()


def test_publish_page_explains_an_invalid_draft(admin, theme, settings):
    # Issue #186: the draft uses a base the project no longer allows (the setting
    # changed after it was saved), so publishing is refused with the reason.
    Theme.objects.filter(pk=theme.pk).update(light_base="cupcake")
    settings.CAPY_THEME_BUILTIN_THEMES = ["light", "dark"]
    response = admin.post(publish_url(theme), {"note": ""}, follow=True)
    content = response.content.decode()
    assert "Can&#x27;t publish:" in content
    assert "&#x27;cupcake&#x27; is not an available light daisyUI theme." in content
    assert not ThemeRevision.objects.exists()
