"""The theme form's shape and effect fields."""

from django import forms

from ..css.shape import EFFECTS, SIZES
from ..themes.catalogue import builtin_values


def add_fields(form_class):
    for name, (_variable, unit, low, high, field_label, help_text) in SIZES.items():
        form_class.base_fields[f"shape_{name}"] = form_class.declared_fields[f"shape_{name}"] = (
            forms.DecimalField(
                required=False,
                min_value=low,
                max_value=high,
                decimal_places=4,
                label=f"{field_label} ({unit})",
                help_text=f"{help_text} Leave blank to use the base theme's value "
                "(shown greyed out).",
            )
        )
    for name, (_variable, field_label, help_text) in EFFECTS.items():
        form_class.base_fields[f"shape_{name}"] = form_class.declared_fields[f"shape_{name}"] = (
            forms.ChoiceField(
                required=False,
                choices=[("", "From the base theme"), ("on", "On"), ("off", "Off")],
                label=field_label,
                help_text=help_text,
            )
        )


def set_initial(form):
    shape = form.instance.settings.get("shape", {})
    base = builtin_values(form.instance.light_base) or {}
    for name, (variable, unit, *_rest) in SIZES.items():
        field = form.fields[f"shape_{name}"]
        field.initial = shape.get(name)
        field.widget.attrs["placeholder"] = base.get(variable, "").removesuffix(unit)
        field.widget.attrs["step"] = "any"
    for name in EFFECTS:
        if name in shape:
            form.fields[f"shape_{name}"].initial = "on" if shape[name] else "off"


def clean(form, cleaned, settings):
    shape = {}
    for name in SIZES:
        value = cleaned.get(f"shape_{name}")
        if value is not None:
            shape[name] = float(value)
    for name in EFFECTS:
        choice = cleaned.get(f"shape_{name}")
        if choice in ("on", "off"):
            shape[name] = choice == "on"
    if shape:
        settings["shape"] = shape
    else:
        settings.pop("shape", None)
