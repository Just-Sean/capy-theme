"""Previewing unsaved editor values with the same code as publishing."""

import copy

from django.core.exceptions import ValidationError

from ..colors.color_math import to_hex, to_oklch
from ..colors.values import contrast_report, effective_values
from ..css.custom import without_custom_css
from ..css.stylesheet import snapshot_css
from ..fonts.library import external_stylesheets
from ..themes.validation import validate_base, validate_settings
from .page_images import page_images

# The settings the editor manages. Anything else in a theme's settings (site
# name and so on) is kept as it is.
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

    `data` may have "base" and "settings" (with "colors" and "shape"). Colors can
    be in any CSS format; they're converted to OKLCH.
    Raises ValidationError (with every problem) if anything is invalid.
    The theme itself and the database are never changed.
    """
    draft = copy.copy(theme)
    errors = []
    if "base" in data:
        draft.base = str(data["base"])
        try:
            validate_base(draft.base)
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
    colors = settings.get("colors")
    if isinstance(colors, dict):
        for name, value in colors.items():
            try:
                colors[name] = to_oklch(str(value))
            except ValueError:
                errors.append(f"{name}: {value!r} isn't a color.")
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
    values = effective_values(snapshot)
    return {
        "css": snapshot_css(snapshot, f"capy-theme editor: preview of {theme.name}"),
        "values": values,
        # Hex for the browser's color pickers, keyed like "primary" or "base-100".
        "hex": {
            key.removeprefix("--color-"): to_hex(value, alpha=False)
            for key, value in values.items()
            if key.startswith("--color-")
        },
        "contrast": contrast_report(values),
        "settings": without_custom_css(draft.settings),  # the editor doesn't edit it
        "base": draft.base,
        "scheme": draft.scheme,
        # External font stylesheets (e.g. Adobe Fonts) the page must link.
        "stylesheets": external_stylesheets(snapshot.get("fonts")),
        # The draft's logos and icon, shown on the page before publishing (#271).
        "page_images": page_images(snapshot),
    }
