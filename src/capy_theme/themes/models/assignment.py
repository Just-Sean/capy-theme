"""Which theme is live: the default assignment and scheduled ones."""

import re

from django.core.exceptions import ValidationError
from django.db import models

from .theme import Theme

# A domain such as example.com or localhost, or an IPv6 address in brackets.
DOMAIN = re.compile(
    r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*|\[[0-9a-f:.]+\]"
)


class ThemeAssignment(models.Model):
    """Which theme is active, on every site or on one domain.

    The default assignment has no dates; change it with active.activate().
    Scheduled assignments have a start and/or end date and win while they're
    running (start ≤ now < end), e.g. a holiday theme. An assignment with a site
    (domain) applies only there and wins over the ones for every site.
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
        if not self.is_scheduled:
            return f"{self.theme} (default)"
        return f"{self.theme} ({self.starts_at or '…'} to {self.ends_at or '…'})"

    @property
    def is_scheduled(self):
        return self.starts_at is not None or self.ends_at is not None

    def is_running(self, now):
        """True if `now` is inside the dates (start included, end not)."""
        return (self.starts_at is None or self.starts_at <= now) and (
            self.ends_at is None or now < self.ends_at
        )

    def clean(self):
        super().clean()
        self.site = self.site.strip().lower()
        if self.site and not DOMAIN.fullmatch(self.site):
            raise ValidationError(
                {"site": "Just the domain, e.g. example.com (no https://, path or port)."}
            )
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "The end must be after the start."})
        if self.theme_id and self.theme.live_revision_id is None:
            raise ValidationError({"theme": "Publish this theme before scheduling it."})


class ScheduledTheme(ThemeAssignment):
    """The admin's view of scheduled assignments (those with dates)."""

    class Meta:
        proxy = True
        verbose_name = "scheduled theme"
        verbose_name_plural = "theme schedule"


class SiteTheme(ThemeAssignment):
    """The admin's view of the themes for particular domains (multiple sites)."""

    class Meta:
        proxy = True
        verbose_name = "site theme"
        verbose_name_plural = "site themes"
