"""The theme form's images: logo slots, icon, sharing image, backgrounds.

Each slot is one field (admin/slot_image.py): its current image, a choice of
earlier uploads, a new upload and the alt text. A new upload is stored and
chosen when the theme is saved (save_images); nothing changes for visitors until
the theme is published.
"""

from django import forms

from ..images.assets import store_asset
from ..images.icons import SETTINGS as ICON_SETTINGS
from ..images.logos import HEIGHTS
from ..images.slot_text import empty_text, help_text
from ..images.slots import SLOTS
from .slot_image import SlotImageField

TWO_ALT_EDITS = (
    "This image is shown twice on this page and its alt text was changed differently "
    "in each box. Change it in one box only."
)
CHOOSE_AGAIN = (
    "Choose the file again: files aren't kept when another part of the page has an error."
)


def image_field_name(slot):
    return f"image_{slot}"


# The image slots with a choice in the form (from slots.json).
CHOOSABLE = tuple(SLOTS)


def add_fields(form_class):
    for slot in CHOOSABLE:
        name = image_field_name(slot)
        form_class.base_fields[name] = form_class.declared_fields[name] = SlotImageField(
            slot,
            label=SLOTS[slot][0],
            help_text=help_text(slot),
        )
    for name, (field_label, default) in HEIGHTS.items():
        form_class.base_fields[f"logo_{name}"] = form_class.declared_fields[f"logo_{name}"] = (
            forms.IntegerField(
                required=False,
                min_value=16,
                max_value=200,
                label=field_label,
                help_text=f"Blank for {default} px.",
            )
        )
    form_class.base_fields["icon_background"] = form_class.declared_fields["icon_background"] = (
        forms.RegexField(
            regex=r"^#[0-9a-fA-F]{6}$",
            required=False,
            label=ICON_SETTINGS["background"][0],
            help_text=ICON_SETTINGS["background"][1],
            error_messages={"invalid": "Use a hex color like #ffffff."},
        )
    )
    form_class.base_fields["icon_padding"] = form_class.declared_fields["icon_padding"] = (
        forms.FloatField(
            required=False,
            min_value=0,
            max_value=25,
            label=ICON_SETTINGS["padding"][0],
            help_text=ICON_SETTINGS["padding"][1],
        )
    )


def set_initial(form):
    """A choice of this theme's uploaded images for each slot."""
    chosen = form.instance.settings.get("images", {})
    assets = list(form.instance.assets.all()) if form.instance.pk else []
    for slot in CHOOSABLE:
        mine = [a for a in assets if a.slot == slot]
        widget = form.fields[image_field_name(slot)].widget
        widget.choices = [("", "Image to use: None")] + [
            (a.pk, f"{a.original.name.rsplit('/', 1)[-1]} ({a.width} × {a.height})") for a in mine
        ]
        widget.assets = {str(a.pk): a for a in mine}
        widget.empty_text = empty_text(slot)
        widget.attrs["aria-label"] = f"{SLOTS[slot][0]}: image to use"
        widget.saved = str(chosen.get(slot, ""))
        form.fields[image_field_name(slot)].initial = widget.saved
    heights = form.instance.settings.get("logo", {})
    for name in HEIGHTS:
        form.fields[f"logo_{name}"].initial = heights.get(name)
    icon = form.instance.settings.get("icon", {})
    for name in ICON_SETTINGS:
        form.fields[f"icon_{name}"].initial = icon.get(name)


def _alt_edits(form, cleaned):
    """{image id: new alt text} for the alt text boxes that were changed. An image
    shown in two boxes is only changed by a box that differs from its saved text;
    two different changes for one image are an error."""
    edits = {}
    for slot in CHOOSABLE:
        name = image_field_name(slot)
        value = cleaned.get(name) or {}
        asset = form.fields[name].widget.assets.get(str(value.get("alt_for") or ""))
        alt = value.get("alt")
        if asset is None or alt is None or alt == asset.alt_text:
            continue
        if edits.get(asset.pk, alt) != alt:
            form.add_error(name, TWO_ALT_EDITS)
            continue
        edits[asset.pk] = alt
    return edits


def clean(form, cleaned, settings):
    # Also on the (unsaved) theme, which the Media list gets, so it can refuse a
    # different edit of the same image's alt text there (admin/inlines.py).
    form.capy_alt_edits = form.instance.capy_alt_edits = _alt_edits(form, cleaned)
    images = {
        slot: cleaned[image_field_name(slot)]["choice"]
        for slot in CHOOSABLE
        if (cleaned.get(image_field_name(slot)) or {}).get("choice")
    }
    # Slots without admin fields are kept as they are.
    images = {
        **{k: v for k, v in settings.get("images", {}).items() if k not in CHOOSABLE},
        **images,
    }
    if images:
        settings["images"] = images
    else:
        settings.pop("images", None)
    heights = {
        name: cleaned[f"logo_{name}"] for name in HEIGHTS if cleaned.get(f"logo_{name}") is not None
    }
    if heights:
        settings["logo"] = heights
    else:
        settings.pop("logo", None)
    icon = {}
    if cleaned.get("icon_background"):
        icon["background"] = cleaned["icon_background"].lower()
    if cleaned.get("icon_padding") is not None:
        icon["padding"] = float(cleaned["icon_padding"])
    if icon:
        settings["icon"] = icon
    else:
        settings.pop("icon", None)


def ask_to_choose_again(form):
    """Browsers don't keep a chosen file when the page comes back with errors (in
    the form or in a list below it), so say so next to each slot that had one.
    Called by ThemeAdmin when the page is shown again after a failed save (#271)."""
    cleaned = getattr(form, "cleaned_data", None) or {}
    for slot in CHOOSABLE:
        name = image_field_name(slot)
        value = cleaned.get(name) or {}
        if value.get("clean") and name not in form.errors:
            form.add_error(name, CHOOSE_AGAIN)


def save_images(form, theme):
    """After the theme is saved: store new uploads and choose them, and save edited
    alt text. A new upload in a slot replaces the choice made in the list."""
    images = theme.settings.get("images", {})
    assets = {a.pk: a for a in theme.assets.all()}
    changed = False
    for slot in CHOOSABLE:
        value = form.cleaned_data.get(image_field_name(slot)) or {}
        if value.get("clean"):
            asset = store_asset(theme, slot, value["clean"], value["upload_alt"])
            images[slot] = asset.pk
            changed = True
    # Alt text typed for the images the page showed (never another one).
    for pk, alt in getattr(form, "capy_alt_edits", {}).items():
        if pk in assets:
            assets[pk].alt_text = alt
            assets[pk].save(update_fields=["alt_text"])
    if changed:
        theme.settings["images"] = images
        theme.save()
