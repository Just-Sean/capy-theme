"""Tests for revisions and publishing (issue #6)."""

import pytest
from django.core.exceptions import ValidationError
from django.urls import reverse

from capy_theme.models import Theme, ThemeRevision
from capy_theme.publishing import NothingToPublish, publish

pytestmark = pytest.mark.django_db


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")


# publish()


def test_new_theme_is_unpublished(theme):
    assert theme.live_revision is None
    assert theme.has_unpublished_changes


def test_publish_creates_revision_with_who_and_when(theme, user):
    revision = publish(theme, user=user, note="First version")
    theme.refresh_from_db()
    assert theme.live_revision == revision
    assert revision.number == 1
    assert revision.published_by == user
    assert revision.published_at is not None
    assert revision.note == "First version"
    assert revision.snapshot == {"light_base": "light", "dark_base": "dark", "settings": {}}
    assert not theme.has_unpublished_changes


def test_editing_changes_only_the_draft(theme, user):
    publish(theme, user=user)
    theme.light_base = "cupcake"
    theme.save()
    theme.refresh_from_db()
    assert theme.live_revision.snapshot["light_base"] == "light"
    assert theme.has_unpublished_changes


def test_each_publish_adds_a_numbered_revision(theme, user):
    publish(theme, user=user)
    theme.light_base = "cupcake"
    theme.save()
    second = publish(theme, user=user)
    theme.refresh_from_db()
    assert second.number == 2
    assert theme.live_revision == second
    assert second.snapshot["light_base"] == "cupcake"
    assert [r.number for r in theme.revisions.all()] == [2, 1]
    # The first revision is unchanged.
    assert theme.revisions.get(number=1).snapshot["light_base"] == "light"


def test_publishing_without_changes_is_refused(theme, user):
    publish(theme, user=user)
    with pytest.raises(NothingToPublish):
        publish(theme, user=user)
    assert theme.revisions.count() == 1


def test_renaming_needs_no_publish(theme, user):
    publish(theme, user=user)
    theme.name = "Renamed"
    theme.slug = "renamed"
    theme.save()
    theme.refresh_from_db()
    assert not theme.has_unpublished_changes


def test_invalid_draft_cant_be_published(theme, user, settings):
    settings.CAPY_THEME_BUILTIN_THEMES = ["cupcake", "dark"]  # "light" no longer allowed
    with pytest.raises(ValidationError):
        publish(theme, user=user)
    assert not ThemeRevision.objects.exists()


def test_saving_a_stale_copy_doesnt_unpublish(theme, user):
    stale = Theme.objects.get(pk=theme.pk)  # e.g. an edit form opened before publishing
    publish(theme, user=user)
    stale.light_base = "cupcake"
    stale.save()
    theme.refresh_from_db()
    assert theme.live_revision is not None
    assert theme.live_revision.number == 1


def test_publish_without_a_user(theme):
    revision = publish(theme)
    assert revision.published_by is None


def test_snapshot_is_a_copy_not_shared_with_the_draft(theme, user):
    revision = publish(theme, user=user)
    theme.snapshot()["settings"]["changed"] = True
    assert revision.snapshot["settings"] == {}


def test_deleting_a_user_keeps_their_revisions(theme, user):
    revision = publish(theme, user=user)
    user.delete()
    revision.refresh_from_db()
    assert revision.published_by is None


def test_deleting_a_theme_deletes_its_revisions(theme, user):
    publish(theme, user=user)
    theme.delete()
    assert not ThemeRevision.objects.exists()


# The admin


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


def test_staff_without_change_permission_cant_publish(client, theme, django_user_model):
    viewer = django_user_model.objects.create_user("viewer", password="pw", is_staff=True)
    client.force_login(viewer)
    response = client.post(publish_url(theme), {"note": ""})
    assert response.status_code == 403
    assert not ThemeRevision.objects.exists()
