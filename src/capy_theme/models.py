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

from .catalogue import builtin_values
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
    logo = models.ImageField(
        upload_to="capy_theme/logos/",
        blank=True,
        help_text="The main logo (PNG, JPEG, GIF or WebP). Shown at the size it's uploaded.",
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
        permissions = [
            ("publish_theme", "Can publish, activate and restore themes"),
            ("edit_custom_css", "Can edit a theme's custom CSS"),
            ("import_theme", "Can import themes"),
        ]

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
            # The bases' full values are copied too, so a later daisyUI update
            # can't change or break a published theme. None if the base no
            # longer exists (such a draft can't be published).
            "light_values": builtin_values(self.light_base),
            "dark_values": builtin_values(self.dark_base),
            # The stored file's name. Replacing the logo stores a new file and
            # never overwrites the old one, so older revisions keep theirs.
            "logo": self.logo.name or "",
            "settings": copy.deepcopy(self.settings),
        }

    def base_changes(self):
        """Return notes on daisyUI changes to the live revision's base themes.

        The live revision keeps the base values saved when it was published. If
        the daisyUI catalogue the module now ships has different values for a
        base, or no longer has it, this explains that the site still uses the
        saved version. Empty if nothing changed or the theme isn't published.
        """
        live = self.live_revision
        if live is None:
            return []
        notes = []
        for scheme in ("light", "dark"):
            name = live.snapshot.get(f"{scheme}_base")
            current = builtin_values(name)
            if current is None:
                notes.append(
                    f"“{name}” no longer exists in daisyUI. Your site keeps using the saved "
                    f"version. Choose a new {scheme} base to publish changes."
                )
            elif current != live.snapshot.get(f"{scheme}_values"):
                notes.append(
                    f"daisyUI has changed “{name}” since this theme was published. Your site "
                    "keeps using the saved version. Publish again to use daisyUI's new one."
                )
        return notes

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
    snapshot = models.JSONField(
        help_text="The theme's light and dark base names and their values, logo and settings."
    )
    css_version = models.CharField(
        max_length=16,
        unique=True,
        editable=False,
        help_text="Short hash naming this revision's stylesheet: /theme/<css_version>.css",
    )
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


class ThemeAssignment(models.Model):
    """Which theme is active on the site.

    For now there's one default assignment: no site and no dates. The site and
    date fields exist from the start for multiple sites (8.2) and scheduling
    (6.3), and are ignored until then. Change it with active.activate(), not
    directly.
    """

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="assignments")
    site = models.CharField(
        max_length=255, blank=True, help_text="Domain this applies to. Blank means every site."
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Only one default (undated) assignment per site.
            models.UniqueConstraint(
                fields=["site"],
                condition=models.Q(starts_at__isnull=True, ends_at__isnull=True),
                name="one_default_assignment_per_site",
            ),
        ]

    def __str__(self):
        return f"{self.theme} on {self.site or 'every site'}"
