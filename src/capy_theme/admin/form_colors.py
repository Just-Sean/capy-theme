"""The theme form's colour fields: 20 colours per mode, with contrast notes."""

from ..colors.fields import ColorField
from ..colors.names import COLOR_GROUPS, COLOR_NAMES, SCHEMES, label
from ..colors.values import contrast_report, draft_values
from ..themes.catalogue import builtin_values


def color_field_name(scheme, name):
    """The form field for one colour override, e.g. color_light_base_100."""
    return f"color_{scheme}_{name.replace('-', '_')}"


def add_fields(form_class):
    for scheme in SCHEMES:
        for name in COLOR_NAMES:
            # Added to both, so the admin's own copy of the form (built with
            # modelform_factory) knows these fields too.
            form_class.base_fields[color_field_name(scheme, name)] = form_class.declared_fields[
                color_field_name(scheme, name)
            ] = ColorField(
                required=False,
                label=label(name),
                help_text="Any colour format (hex, rgb, hsl, oklch); saved as OKLCH. "
                "Leave blank to use the base theme's colour (shown greyed out).",
            )


def set_initial(form):
    colors = form.instance.settings.get("colors", {})
    for scheme in SCHEMES:
        base = builtin_values(getattr(form.instance, f"{scheme}_base")) or {}
        for name in COLOR_NAMES:
            field = form.fields[color_field_name(scheme, name)]
            field.initial = colors.get(scheme, {}).get(name, "")
            field.widget.attrs["placeholder"] = base.get(f"--color-{name}", "")
    if form.instance.pk:
        _add_contrast_ratings(form)


def _add_contrast_ratings(form):
    """Show each colour's WCAG contrast rating (from the saved draft) in its help text."""
    for scheme in SCHEMES:
        values = draft_values(form.instance, scheme)
        if not values:
            continue
        for entry in contrast_report(values):
            note = _rating_note(entry)
            for name in (entry["background"], entry["text"]):
                field = form.fields[color_field_name(scheme, name)]
                field.help_text = f"{field.help_text} {note}"


def clean(form, cleaned, settings):
    colors = {}
    for scheme in SCHEMES:
        chosen = {}
        for name in COLOR_NAMES:
            value = (cleaned.get(color_field_name(scheme, name)) or "").strip()
            if value:
                chosen[name] = value
        if chosen:
            colors[scheme] = chosen
    if colors:
        settings["colors"] = colors
    else:
        settings.pop("colors", None)


def _pair(entry):
    return f"{label(entry['background'])} / {label(entry['text'])}"


def _rating_note(entry):
    words = {"AAA": "passes AAA", "AA": "passes AA", "fail": "⚠ fails AA, hard to read"}
    return f"Contrast {_pair(entry)}: {entry['ratio']}:1, {words[entry['rating']]}."


def color_fieldsets():
    """Admin fieldsets for the colour overrides: Basic, Advanced, Expert, per mode."""
    sets = []
    for scheme in SCHEMES:
        for group, names in COLOR_GROUPS.items():
            classes = [] if group == "Basic" else ["collapse"]
            sets.append(
                (
                    f"{scheme.capitalize()} colours: {group}",
                    {
                        "fields": [color_field_name(scheme, n) for n in names],
                        "classes": classes,
                    },
                )
            )
    return sets
