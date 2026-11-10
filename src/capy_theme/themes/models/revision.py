"""ThemeRevision: a published copy of a theme's look."""

from django.conf import settings as django_settings
from django.db import models
from django.utils import timezone

from .theme import Theme


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
