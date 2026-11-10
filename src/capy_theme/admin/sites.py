"""Site themes in the admin: a different theme for particular domains.

One install can serve several domains. A site theme makes that domain use its own
theme; every other domain uses the theme activated for every site. Needs the
publish_theme permission, like activating.
"""

from django import forms
from django.contrib import admin

from ..models import SiteTheme, Theme
from .publish_permission import PublishPermissionMixin


class SiteThemeForm(forms.ModelForm):
    class Meta:
        model = SiteTheme
        fields = ["site", "theme"]
        labels = {"site": "Domain"}
        help_texts = {
            "site": "e.g. shop.example.com or localhost (no https://, path or port). "
            "It must also be in the project's ALLOWED_HOSTS.",
        }

    def clean_site(self):
        site = self.cleaned_data["site"].strip().lower()
        if not site:
            raise forms.ValidationError(
                "Give a domain. For every site, use the Activate action on the theme list."
            )
        return site


@admin.register(SiteTheme)
class SiteThemeAdmin(PublishPermissionMixin, admin.ModelAdmin):
    form = SiteThemeForm
    list_display = ["site", "theme"]
    list_select_related = ["theme"]
    ordering = ["site"]
    search_fields = ["site"]

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .exclude(site="")
            .filter(starts_at__isnull=True, ends_at__isnull=True)
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "theme":
            kwargs["queryset"] = Theme.objects.filter(live_revision__isnull=False)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
