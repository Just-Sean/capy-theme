"""Database models for this module.

To link to users, use settings.AUTH_USER_MODEL (never import a project's User):

    from django.conf import settings
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
"""

import copy
import uuid

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .validation import validate_base, validate_settings


class Theme(models.Model):
    """A saved theme: two built-in daisyUI bases plus the overrides in `settings`.

    The fields here are the draft: editing a theme changes only the draft.
    Publishing (see publishing.py) copies the draft's look into a ThemeRevision,
    and `live_revision` points at the one pages use.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    # Names of built-in daisyUI themes (see catalogue.py). Not stored as model
    # `choices`, because the list depends on the CAPY_THEME_BUILTIN_THEMES setting
    # and choices would end up in migrations. Checked in clean() instead.
    light_base = models.CharField(
        max_length=50, default="light", help_text="The built-in daisyUI theme used in light mode."
    )
    dark_base = models.CharField(
        max_length=50, default="dark", help_text="The built-in daisyUI theme used in dark mode."
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_settings],
        help_text="Every override on top of the base themes.",
    )
    live_revision = models.ForeignKey(
        "ThemeRevision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
        help_text="The published revision pages use. Empty until the theme is first published.",
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Checked on every save, not only in forms, so bad data can't be saved
        # from code either.
        validate_settings(self.settings)
        self.clean()
        # Only publishing changes live_revision (it saves with update_fields).
        # An ordinary save of an existing theme leaves it alone, so a copy loaded
        # before someone published can't overwrite the live revision.
        if not self._state.adding and kwargs.get("update_fields") is None:
            kwargs["update_fields"] = [
                field.name
                for field in self._meta.concrete_fields
                if not field.primary_key and field.name != "live_revision"
            ]
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
            try:
                validate_base(getattr(self, field), scheme)
            except ValidationError as error:
                errors[field] = error.messages
        if errors:
            raise ValidationError(errors)

    def snapshot(self):
        """Return the draft's look: everything a revision copies when published.

        The name and slug are admin labels, so they aren't part of it: renaming
        a theme takes effect without publishing.
        """
        return {
            "light_base": self.light_base,
            "dark_base": self.dark_base,
            "settings": copy.deepcopy(self.settings),
        }

    @property
    def has_unpublished_changes(self):
        """True if the draft's look differs from the live revision (or was never published)."""
        if self.live_revision is None:
            return True
        return self.snapshot() != self.live_revision.snapshot


class ThemeRevision(models.Model):
    """A published copy of a theme's look. Never edited after it's created.

    Created only by publishing.publish(). Kept for history and, later, compare
    and restore.
    """

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="revisions")
    number = models.PositiveIntegerField(help_text="1 for the theme's first publish, then 2, 3…")
    snapshot = models.JSONField(help_text="The theme's light base, dark base and settings.")
    note = models.TextField(blank=True, help_text="Why it was published (optional).")
    published_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["theme", "-number"]
        constraints = [
            models.UniqueConstraint(fields=["theme", "number"], name="unique_revision_number"),
        ]

    def __str__(self):
        return f"{self.theme} revision {self.number}"
