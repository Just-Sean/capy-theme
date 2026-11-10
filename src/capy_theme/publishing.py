"""Publishing: turning a theme's draft into the live revision pages use."""

from django.db import transaction
from django.db.models import Max

from .models import Theme, ThemeRevision
from .validation import validate_settings


class NothingToPublish(Exception):
    """Raised when the draft's look already matches the live revision."""


def publish(theme, user=None, note=""):
    """Publish the theme's draft and return the new ThemeRevision.

    Copies the draft's look (light base, dark base, settings) into a new revision
    numbered one higher than the last, records who published it and when, and
    makes it the theme's live revision.

    Raises NothingToPublish if nothing changed since the last publish, and
    ValidationError if the draft isn't valid (e.g. a base the project no
    longer allows).
    """
    original = theme
    with transaction.atomic():
        # Lock the theme row so two publishes at once can't get the same number.
        theme = Theme.objects.select_for_update().get(pk=theme.pk)
        if not theme.has_unpublished_changes:
            raise NothingToPublish("Nothing to publish: the draft matches the live revision.")

        validate_settings(theme.settings)
        theme.clean()

        last = theme.revisions.aggregate(last=Max("number"))["last"] or 0
        revision = ThemeRevision.objects.create(
            theme=theme,
            number=last + 1,
            snapshot=theme.snapshot(),
            note=note,
            published_by=user if user is not None and user.is_authenticated else None,
        )
        theme.live_revision = revision
        theme.save(update_fields=["live_revision"])
    # Keep the caller's copy up to date too.
    original.live_revision = revision
    return revision
