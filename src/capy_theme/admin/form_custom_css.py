"""The theme form's custom CSS fields, for users with the edit_custom_css permission.

ThemeAdmin.get_form() sets `can_edit_custom_css` on the form class. Without it the
fields are removed, so the CSS is neither shown nor changed when saving the form.
"""

from django import forms

from ..css.custom import MAX_LENGTH

FIELDS = ("custom_css", "custom_css_enabled")


def add_fields(form_class):
    form_class.base_fields["custom_css"] = form_class.declared_fields["custom_css"] = (
        forms.CharField(
            required=False,
            max_length=MAX_LENGTH,
            label="Custom CSS",
            widget=forms.Textarea(attrs={"rows": 12, "cols": 80, "spellcheck": "false"}),
            help_text="Loaded after the theme stylesheet on every page that uses "
            "{% theme_head %}, once published. For anything the settings don't cover.",
        )
    )
    form_class.base_fields["custom_css_enabled"] = form_class.declared_fields[
        "custom_css_enabled"
    ] = forms.BooleanField(
        required=False,
        initial=True,
        label="Use the custom CSS",
        help_text="Untick to switch it off without deleting it (takes effect when published).",
    )


def set_initial(form):
    if not getattr(form, "can_edit_custom_css", False):
        for name in FIELDS:
            form.fields.pop(name, None)
        return
    chosen = form.instance.settings.get("custom_css", {})
    form.fields["custom_css"].initial = chosen.get("css", "")
    form.fields["custom_css_enabled"].initial = chosen.get("enabled", True)


def clean(form, cleaned, settings):
    if not getattr(form, "can_edit_custom_css", False):
        return  # left exactly as it was
    css = (cleaned.get("custom_css") or "").strip()
    if css:
        settings["custom_css"] = {"css": css, "enabled": bool(cleaned.get("custom_css_enabled"))}
    else:
        settings.pop("custom_css", None)  # nothing to store, switched on or off
