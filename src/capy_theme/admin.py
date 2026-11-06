from django import forms
from django.contrib import admin

from .catalogue import get_builtin_themes
from .models import Theme


def _base_choices(scheme):
    return [(theme.name, theme.name) for theme in get_builtin_themes() if theme.scheme == scheme]


class ThemeForm(forms.ModelForm):
    """Offers only light themes as the light base and dark themes as the dark base."""

    light_base = forms.ChoiceField()
    dark_base = forms.ChoiceField()

    class Meta:
        model = Theme
        fields = ["name", "slug", "light_base", "dark_base", "settings"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Built per form, so a change to CAPY_THEME_BUILTIN_THEMES shows immediately.
        for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
            self.fields[field].choices = _base_choices(scheme)
            self.fields[field].help_text = Theme._meta.get_field(field).help_text
            self.fields[field].initial = Theme._meta.get_field(field).default


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    form = ThemeForm
    list_display = ["name", "slug", "light_base", "dark_base", "updated_at"]
    list_filter = ["light_base", "dark_base"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["public_id", "created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["name", "slug"]}),
        ("Base themes", {"fields": ["light_base", "dark_base"]}),
        ("Overrides", {"fields": ["settings"]}),
        ("Details", {"fields": ["public_id", "created_at", "updated_at"]}),
    ]
