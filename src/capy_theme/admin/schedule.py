"""The theme schedule in the admin: themes that are live between two dates."""

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import ScheduledTheme, Theme
from ..themes.active import theme_at
from .publish_permission import PublishPermissionMixin


class ScheduledThemeForm(forms.ModelForm):
    class Meta:
        model = ScheduledTheme
        fields = ["theme", "site", "starts_at", "ends_at"]
        help_texts = {
            "site": "Only on this domain (e.g. shop.example.com). Blank: every site.",
            "starts_at": "When it goes live. Blank: straight away.",
            "ends_at": "When the site's default theme returns. Blank: until removed.",
        }

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("starts_at") and not cleaned.get("ends_at"):
            raise ValidationError(
                "Give a start or an end date. To change the site's default theme, use "
                "the Activate action on the theme list instead."
            )
        return cleaned


@admin.register(ScheduledTheme)
class ScheduledThemeAdmin(PublishPermissionMixin, admin.ModelAdmin):
    """Themes that are live between two dates, e.g. a holiday theme.

    While one is running it wins over the site's default theme (the most recently
    started one if several overlap); afterwards the default returns by itself.
    Needs the publish_theme permission, like activating.
    """

    form = ScheduledThemeForm
    list_display = ["theme", "site_name", "starts_at", "ends_at", "status"]
    list_select_related = ["theme"]
    ordering = ["starts_at"]

    def get_queryset(self, request):
        return super().get_queryset(request).exclude(starts_at__isnull=True, ends_at__isnull=True)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "theme":
            kwargs["queryset"] = Theme.objects.filter(live_revision__isnull=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Site", ordering="site")
    def site_name(self, assignment):
        return assignment.site or "Every site"

    @admin.display(description="Status")
    def status(self, assignment):
        now = timezone.now()
        if assignment.is_running(now):
            live = theme_at(now, assignment.site)
            return "Running" if live == assignment.theme else "Running (overlapped)"
        if assignment.starts_at and assignment.starts_at > now:
            return "Upcoming"
        return "Finished"
