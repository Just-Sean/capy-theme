"""Publishing: turning a theme's draft into the live revision pages use."""

from django.db import transaction
from django.db.models import Max

from ..css.stylesheet import css_version
from ..images.icons import make_icons
from ..models import ThemeRevision
from .validation import validate_settings

NOTHING_TO_PUBLISH = "Nothing to publish: the draft matches the live revision."


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
    if not theme.has_unpublished_changes:
        raise NothingToPublish(NOTHING_TO_PUBLISH)

    validate_settings(theme.settings)
    theme.clean()
    snapshot = theme.snapshot()
    # The favicons and app icons are made now, so pages only link to files.
    make_icons(snapshot)
    with transaction.atomic():
        number = (theme.revisions.aggregate(last=Max("number"))["last"] or 0) + 1
        revision = ThemeRevision.objects.create(
            theme=theme,
            number=number,
            snapshot=snapshot,
            css_version=css_version(theme.pk, number, snapshot),
            note=note,
            published_by=user if user is not None and user.is_authenticated else None,
        )
        theme.live_revision = revision
        theme.save(update_fields=["live_revision"])
    return revision
