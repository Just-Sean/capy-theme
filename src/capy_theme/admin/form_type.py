"""The theme form's font and type scale fields."""

from django import forms

from ..css.typography import TYPE_SETTINGS
from ..fonts.library import ROLES
from ..fonts.models import Font


def add_fields(form_class):
    for role, role_label in ROLES.items():
        form_class.base_fields[f"font_{role}"] = form_class.declared_fields[f"font_{role}"] = (
            forms.ChoiceField(
                required=False,
                label=role_label,
                help_text="Blank uses the project's default font. "
                "Add fonts under Capy Theme → Fonts.",
            )
        )
    for name, (field_label, unit, low, high, _step, help_text) in TYPE_SETTINGS.items():
        form_class.base_fields[f"type_{name}"] = form_class.declared_fields[f"type_{name}"] = (
            forms.DecimalField(
                required=False,
                min_value=low,
                max_value=high,
                decimal_places=2,
                label=f"{field_label} ({unit})" if unit else field_label,
                help_text=f"{help_text} Leave blank to keep the project's own.",
            )
        )


def set_initial(form):
    font_choices = [("", "Default")] + [(str(f.pk), str(f)) for f in Font.objects.all()]
    chosen_fonts = form.instance.settings.get("fonts", {})
    for role in ROLES:
        form.fields[f"font_{role}"].choices = font_choices
        form.fields[f"font_{role}"].initial = str(chosen_fonts.get(role, ""))
    type_settings = form.instance.settings.get("type", {})
    for name, spec in TYPE_SETTINGS.items():
        form.fields[f"type_{name}"].initial = type_settings.get(name)
        form.fields[f"type_{name}"].widget.attrs["step"] = str(spec[4])


def clean(form, cleaned, settings):
    fonts = {role: int(cleaned[f"font_{role}"]) for role in ROLES if cleaned.get(f"font_{role}")}
    if fonts:
        settings["fonts"] = fonts
    else:
        settings.pop("fonts", None)
    type_settings = {}
    for name in TYPE_SETTINGS:
        value = cleaned.get(f"type_{name}")
        if value is not None:
            type_settings[name] = int(value) if name == "heading_weight" else float(value)
    if type_settings:
        settings["type"] = type_settings
    else:
        settings.pop("type", None)
