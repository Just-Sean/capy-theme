"""The theme edit form: the base and branding, plus each area's fields."""

from django import forms

from ..models import Theme
from ..themes.catalog import get_builtin_themes
from . import form_colors, form_custom_css, form_images, form_shape, form_type

# Each area of the form: its fields, their current values, and reading them back.
PARTS = (form_colors, form_type, form_shape, form_images, form_custom_css)


def _base_choices():
    """Each built-in theme, labeled with its scheme, e.g. "cupcake (light)"."""
    return [(theme.name, f"{theme.name} ({theme.scheme})") for theme in get_builtin_themes()]


class ThemeForm(forms.ModelForm):
    """The theme edit form.

    A theme is a single scheme — its base theme sets whether it's light or dark.
    Values stored in `settings` (site name, tagline, logo alt text) get their own
    fields here and are written back into `settings` on save.
    """

    base = forms.ChoiceField()
    site_name = forms.CharField(
        required=False,
        max_length=100,
        help_text="Shown in headers, and instead of the logo if there's none.",
    )
    tagline = forms.CharField(
        required=False, max_length=200, help_text="A short line describing the site."
    )
    logo_alt = forms.CharField(
        required=False,
        max_length=200,
        label="Logo alt text",
        help_text="Describes the logo for screen readers. Leave blank to use the site name.",
    )

    # Form fields stored as keys in Theme.settings.
    SETTINGS_FIELDS = ["site_name", "tagline", "logo_alt"]

    class Meta:
        model = Theme
        fields = ["name", "slug", "base", "offered_to_visitors"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Built per form, so a change to CAPY_THEME_BUILTIN_THEMES shows immediately.
        self.fields["base"].choices = _base_choices()
        self.fields["base"].help_text = Theme._meta.get_field("base").help_text
        self.fields["base"].initial = Theme._meta.get_field("base").default
        for field in self.SETTINGS_FIELDS:
            self.fields[field].initial = self.instance.settings.get(field, "")
        for part in PARTS:
            part.set_initial(self)

    def clean(self):
        cleaned = super().clean()
        settings = dict(self.instance.settings)
        for field in self.SETTINGS_FIELDS:
            value = cleaned.get(field, "").strip()
            if value:
                settings[field] = value
            else:
                settings.pop(field, None)
        for part in PARTS:
            part.clean(self, cleaned, settings)
        self.instance.settings = settings
        return cleaned


for _part in PARTS:
    _part.add_fields(ThemeForm)
