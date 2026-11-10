"""Saving the editor's values as the draft, and palette suggestions."""

from ..colors.palette import from_logo, from_primary
from .preview import apply_changes


def main_logo_asset(theme):
    """The draft's main logo (light), if it's a raster image; else None."""
    pk = theme.settings.get("images", {}).get("logo_main", {}).get("light")
    asset = theme.assets.filter(pk=pk).first() if pk else None
    return asset if asset and asset.content_type != "image/svg+xml" else None


def suggestions(theme, primary):
    """Palette suggestions for the editor: from `primary`, and from the theme's logo."""
    result = []
    logo = main_logo_asset(theme)
    if logo:
        with logo.original.open("rb") as file:
            suggestion = from_logo(file)
        if suggestion:
            result.append(suggestion)
    if primary:
        result.extend(from_primary(primary))
    return result


def save_draft(theme, data):
    """Store the editor's values in the theme's draft. Visitors see nothing until publish.

    Validated exactly like the preview. Only the bases, colours and shape are
    changed; the rest of the theme (name, branding, mode) is left as it is.
    """
    draft = apply_changes(theme, data)
    theme.light_base = draft.light_base
    theme.dark_base = draft.dark_base
    theme.settings = draft.settings
    theme.save()
    return theme
