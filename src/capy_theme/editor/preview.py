"""Previewing unsaved editor values with the same code as publishing."""

import copy

from django.core.exceptions import ValidationError

from ..colors.color_math import to_hex, to_oklch
from ..colors.names import SCHEMES
from ..colors.values import contrast_report, effective_values
from ..css.custom import without_custom_css
from ..css.stylesheet import snapshot_css
from ..fonts.library import external_stylesheets
from ..themes.validation import validate_base, validate_settings

# The settings the editor manages. Anything else in a theme's settings (site
# name, mode and so on) is kept as it is.
EDITOR_SETTINGS = (
    "colors",
    "shape",
    "fonts",
    "type",
    "images",
    "logo",
    "icon",
)


def apply_changes(theme, data):
    """Return an unsaved copy of `theme` with the editor's values applied.

    `data` may have "light_base", "dark_base" and "settings" (with "colors" and
    "shape"). Colors can be in any CSS format; they're converted to OKLCH.
    Raises ValidationError (with every problem) if anything is invalid.
    The theme itself and the database are never changed.
    """
    draft = copy.copy(theme)
    errors = []
    for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
        if field in data:
            setattr(draft, field, str(data[field]))
            try:
                validate_base(getattr(draft, field), scheme)
            except ValidationError as error:
                errors.extend(error.messages)
    settings = copy.deepcopy(theme.settings)
    changes = data.get("settings", {})
    if not isinstance(changes, dict):
        raise ValidationError("settings must be an object.")
    for key in EDITOR_SETTINGS:
        if key in changes:
            if changes[key]:
                settings[key] = changes[key]
            else:
                settings.pop(key, None)
    for scheme, colors in settings.get("colors", {}).items():
        if not isinstance(colors, dict):
            continue
        for name, value in colors.items():
            try:
                colors[name] = to_oklch(str(value))
            except ValueError:
                errors.append(f"{scheme} {name}: {value!r} isn't a color.")
    if not errors:
        try:
            validate_settings(settings)
        except ValidationError as error:
            errors.extend(error.messages)
    if not errors:
        draft.settings = settings
        try:
            draft.clean()  # e.g. fonts that aren't in the library
        except ValidationError as error:
            errors.extend(error.messages)
    if errors:
        raise ValidationError(errors)
    draft.settings = settings
    return draft


def preview(theme, data):
    """Return what the editor shows for unsaved values: CSS, values and contrast.

    Uses the same code as publishing, so the preview matches what would be
    published. Writes nothing.
    """
    draft = apply_changes(theme, data)
    snapshot = draft.snapshot()
    values = {scheme: effective_values(snapshot, scheme) for scheme in SCHEMES}
    return {
        "css": snapshot_css(snapshot, f"capy-theme editor: preview of {theme.name}"),
        "values": values,
        # Hex for the browser's color pickers, keyed like "primary" or "base-100".
        "hex": {
            scheme: {
                key.removeprefix("--color-"): to_hex(value, alpha=False)
                for key, value in values[scheme].items()
                if key.startswith("--color-")
            }
            for scheme in SCHEMES
        },
        "contrast": {scheme: contrast_report(values[scheme]) for scheme in SCHEMES},
        "settings": without_custom_css(draft.settings),  # the editor doesn't edit it
        "light_base": draft.light_base,
        "dark_base": draft.dark_base,
        # External font stylesheets (e.g. Adobe Fonts) the page must link.
        "stylesheets": external_stylesheets(snapshot.get("fonts")),
    }
