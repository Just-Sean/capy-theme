"""The theme edit form: bases, branding and mode, plus each area's fields."""

from django import forms

from ..models import Theme
from ..themes.catalog import get_builtin_themes
from . import form_colors, form_custom_css, form_images, form_shape, form_type

# Each area of the form: its fields, their current values, and reading them back.
PARTS = (form_colors, form_type, form_shape, form_images, form_custom_css)


def _base_choices(scheme):
    return [(theme.name, theme.name) for theme in get_builtin_themes() if theme.scheme == scheme]


class ThemeForm(forms.ModelForm):
    """The theme edit form.

    Only light themes are offered as the light base and dark themes as the dark
    base. Values stored in `settings` (site name, tagline, logo alt text) get
    their own fields here and are written back into `settings` on save.
    """

    light_base = forms.ChoiceField()
    dark_base = forms.ChoiceField()
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

    default_mode = forms.ChoiceField(
        choices=[
            ("auto", "Auto: follow the visitor's device"),
            ("light", "Light"),
            ("dark", "Dark"),
        ],
        initial="auto",
        required=False,  # missing means "auto"
        help_text="The color mode pages use until a visitor picks one.",
    )
    visitors_can_switch = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Lets visitors choose light, dark or auto with {% theme_mode_toggle %}.",
    )

    # Form fields stored as keys in Theme.settings.
    SETTINGS_FIELDS = ["site_name", "tagline", "logo_alt"]

    class Meta:
        model = Theme
        fields = ["name", "slug", "light_base", "dark_base", "offered_to_visitors"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Built per form, so a change to CAPY_THEME_BUILTIN_THEMES shows immediately.
        for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
            self.fields[field].choices = _base_choices(scheme)
            self.fields[field].help_text = Theme._meta.get_field(field).help_text
            self.fields[field].initial = Theme._meta.get_field(field).default
        for field in self.SETTINGS_FIELDS:
            self.fields[field].initial = self.instance.settings.get(field, "")
        self.fields["default_mode"].initial = self.instance.settings.get("default_mode", "auto")
        self.fields["visitors_can_switch"].initial = self.instance.settings.get(
            "visitors_can_switch", True
        )
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
        # Mode settings are stored only when they differ from the defaults
        # ("auto" and visitors can switch), like the other optional settings.
        if cleaned.get("default_mode") in ("light", "dark"):
            settings["default_mode"] = cleaned["default_mode"]
        else:
            settings.pop("default_mode", None)
        if cleaned.get("visitors_can_switch", True):
            settings.pop("visitors_can_switch", None)
        else:
            settings["visitors_can_switch"] = False
        for part in PARTS:
            part.clean(self, cleaned, settings)
        self.instance.settings = settings
        return cleaned


for _part in PARTS:
    _part.add_fields(ThemeForm)
