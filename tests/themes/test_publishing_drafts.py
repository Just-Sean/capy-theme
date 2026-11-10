"""Tests for publishing a theme's draft as a revision (issue #12)."""

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from capy_theme.models import Theme, ThemeRevision
from capy_theme.themes.publishing import NothingToPublish, publish

pytestmark = pytest.mark.django_db


@pytest.fixture
def theme():
    return Theme.objects.create(name="Main", slug="main")


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_superuser("sean", "sean@example.com", "pw")


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
    assert revision.snapshot["light_base"] == "light"
    assert revision.snapshot["dark_base"] == "dark"
    assert revision.snapshot["settings"] == {}
    assert len(revision.snapshot["light_values"]) == 28
    assert len(revision.snapshot["dark_values"]) == 28
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


def test_two_publishes_cant_get_the_same_number(theme, user):
    publish(theme, user=user)
    with pytest.raises(IntegrityError), transaction.atomic():
        ThemeRevision.objects.create(theme=theme, number=1, snapshot=theme.snapshot())
    assert theme.revisions.count() == 1
