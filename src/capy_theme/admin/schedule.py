"""The theme schedule in the admin: themes that are live between two dates."""

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils import timezone

from ..models import ScheduledTheme, Theme
from ..themes.active import get_active_theme


class ScheduledThemeForm(forms.ModelForm):
    class Meta:
        model = ScheduledTheme
        fields = ["theme", "starts_at", "ends_at"]
        help_texts = {
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
class ScheduledThemeAdmin(admin.ModelAdmin):
    """Themes that are live between two dates, e.g. a holiday theme.

    While one is running it wins over the site's default theme (the most recently
    started one if several overlap); afterwards the default returns by itself.
    Needs the publish_theme permission, like activating.
    """

    form = ScheduledThemeForm
    list_display = ["theme", "starts_at", "ends_at", "status"]
    list_select_related = ["theme"]
    ordering = ["starts_at"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(site="")
            .exclude(starts_at__isnull=True, ends_at__isnull=True)
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "theme":
            kwargs["queryset"] = Theme.objects.filter(live_revision__isnull=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.display(description="Status")
    def status(self, assignment):
        now = timezone.now()
        if assignment.is_running(now):
            return "Running" if get_active_theme() == assignment.theme else "Running (overlapped)"
        if assignment.starts_at and assignment.starts_at > now:
            return "Upcoming"
        return "Finished"

    def _can_publish(self, request):
        return request.user.has_perm("capy_theme.publish_theme")

    def has_add_permission(self, request):
        return self._can_publish(request)

    def has_change_permission(self, request, obj=None):
        return self._can_publish(request)

    def has_delete_permission(self, request, obj=None):
        return self._can_publish(request)

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("capy_theme.view_theme") or self._can_publish(request)

    def has_module_permission(self, request):
        return self.has_view_permission(request)
