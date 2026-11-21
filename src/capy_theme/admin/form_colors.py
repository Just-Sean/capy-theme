"""The theme form's color fields: the 20 colors, with contrast notes."""

from ..colors.fields import ColorField
from ..colors.names import COLOR_GROUPS, COLOR_NAMES, label
from ..colors.values import contrast_report, draft_values
from ..themes.catalog import builtin_values


def color_field_name(name):
    """The form field for one color override, e.g. color_base_100."""
    return f"color_{name.replace('-', '_')}"


def add_fields(form_class):
    for name in COLOR_NAMES:
        # Added to both, so the admin's own copy of the form (built with
        # modelform_factory) knows these fields too.
        form_class.base_fields[color_field_name(name)] = form_class.declared_fields[
            color_field_name(name)
        ] = ColorField(
            required=False,
            label=label(name),
            help_text="Any color format (hex, rgb, hsl, oklch); saved as OKLCH. "
            "Leave blank to use the base theme's color (shown grayed out).",
        )


def set_initial(form):
    colors = form.instance.settings.get("colors", {})
    base = builtin_values(form.instance.base) or {}
    for name in COLOR_NAMES:
        field = form.fields[color_field_name(name)]
        field.initial = colors.get(name, "")
        field.widget.attrs["placeholder"] = base.get(f"--color-{name}", "")
    if form.instance.pk:
        _add_contrast_ratings(form)


def _add_contrast_ratings(form):
    """Show each color's WCAG contrast rating (from the saved draft) in its help text."""
    values = draft_values(form.instance)
    if not values:
        return
    for entry in contrast_report(values):
        note = _rating_note(entry)
        for name in (entry["background"], entry["text"]):
            field = form.fields[color_field_name(name)]
            field.help_text = f"{field.help_text} {note}"


def clean(form, cleaned, settings):
    chosen = {}
    for name in COLOR_NAMES:
        value = (cleaned.get(color_field_name(name)) or "").strip()
        if value:
            chosen[name] = value
    if chosen:
        settings["colors"] = chosen
    else:
        settings.pop("colors", None)


def _pair(entry):
    return f"{label(entry['background'])} / {label(entry['text'])}"


def _rating_note(entry):
    words = {"AAA": "passes AAA", "AA": "passes AA", "fail": "⚠ fails AA, hard to read"}
    return f"Contrast {_pair(entry)}: {entry['ratio']}:1, {words[entry['rating']]}."


def color_fieldsets():
    """Admin fieldsets for the color overrides: Basic, Advanced, Expert."""
    return [
        (
            f"Colors: {group}",
            {"fields": [color_field_name(n) for n in names], "classes": ["collapse"]},
        )
        for group, names in COLOR_GROUPS.items()
    ]
