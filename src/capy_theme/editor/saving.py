"""Saving the editor's values as the draft, and palette suggestions."""

from django.core.exceptions import ValidationError

from ..colors.palette import from_logo, from_primary
from ..images.assets import ALT_MAX
from .preview import apply_changes


def main_logo_asset(theme):
    """The draft's main logo, if it's a raster image; else None."""
    pk = theme.settings.get("images", {}).get("logo_main")
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

    Validated exactly like the preview. Only the editor's settings are changed;
    the rest of the theme (name, branding) is left as it is. `data` may also
    have "alts": {asset id: alt text} for the theme's images (#271).
    """
    draft = apply_changes(theme, data)
    alts = _alts(theme, data.get("alts", {}))
    theme.base = draft.base
    theme.settings = draft.settings
    theme.save()
    for asset, text in alts:
        asset.alt_text = text
        asset.save(update_fields=["alt_text"])
    return theme


def _alts(theme, alts):
    """[(asset, new alt text)] for this theme's images; ValidationError otherwise."""
    if not isinstance(alts, dict):
        raise ValidationError("alts must be an object.")
    assets = {str(a.pk): a for a in theme.assets.all()} if alts else {}
    result = []
    for pk, text in alts.items():
        if str(pk) not in assets or not isinstance(text, str):
            raise ValidationError("That image isn't one of this theme's.")
        if len(text.strip()) > ALT_MAX:
            raise ValidationError(f"Alt text can be at most {ALT_MAX} characters.")
        result.append((assets[str(pk)], text.strip()))
    return result
