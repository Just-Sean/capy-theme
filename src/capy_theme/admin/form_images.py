"""The theme form's images: logo slots, icon, sharing image, backgrounds.

Each slot and mode is one field (admin/slot_image.py): its current image, a choice
of earlier uploads, a new upload and the alt text. A new upload is stored and
chosen when the theme is saved (save_images); nothing changes for visitors until
the theme is published.
"""

from django import forms

from ..images.assets import store_asset
from ..images.icons import SETTINGS as ICON_SETTINGS
from ..images.logos import HEIGHTS
from ..images.slot_text import empty_text, help_text
from ..images.slots import SLOT_MODES, SLOTS
from .slot_image import SlotImageField

CHOOSE_AGAIN = (
    "Choose the file again: files aren't kept when another part of the page has an error."
)


def image_field_name(slot, mode):
    return f"image_{slot}_{mode}"


# The image slots with a choice in the form, and their modes (from slots.json).
CHOOSABLE = SLOT_MODES


def add_fields(form_class):
    for slot, modes in CHOOSABLE.items():
        for mode in modes:
            name = image_field_name(slot, mode)
            form_class.base_fields[name] = form_class.declared_fields[name] = SlotImageField(
                slot,
                mode,
                label=SLOTS[slot][0] if len(modes) == 1 else f"{SLOTS[slot][0]} ({mode})",
                help_text=help_text(slot, mode),
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
    """A choice of this theme's uploaded images for each logo slot and mode."""
    chosen = form.instance.settings.get("images", {})
    assets = list(form.instance.assets.all()) if form.instance.pk else []
    for slot, modes in CHOOSABLE.items():
        mine = [a for a in assets if a.slot == slot]
        for mode in modes:
            widget = form.fields[image_field_name(slot, mode)].widget
            none = "Same as light" if mode == "dark" else "None"
            widget.choices = [("", f"Current image: {none}")] + [
                (
                    a.pk,
                    f"{a.original.name.rsplit('/', 1)[-1]} ({a.width} × {a.height}"
                    f"{', dark' if a.mode == 'dark' else ''})",
                )
                for a in mine
            ]
            widget.assets = {str(a.pk): a for a in mine}
            widget.empty_text = empty_text(slot, mode)
            widget.attrs["aria-label"] = f"{SLOTS[slot][0]} ({mode}): current image"
            form.fields[image_field_name(slot, mode)].initial = str(
                chosen.get(slot, {}).get(mode, "")
            )
    heights = form.instance.settings.get("logo", {})
    for name in HEIGHTS:
        form.fields[f"logo_{name}"].initial = heights.get(name)
    icon = form.instance.settings.get("icon", {})
    for name in ICON_SETTINGS:
        form.fields[f"icon_{name}"].initial = icon.get(name)


def clean(form, cleaned, settings):
    images = {
        slot: {
            mode: cleaned[image_field_name(slot, mode)]["choice"]
            for mode in modes
            if (cleaned.get(image_field_name(slot, mode)) or {}).get("choice")
        }
        for slot, modes in CHOOSABLE.items()
    }
    # Slots without admin fields are kept as they are.
    images = {
        **{k: v for k, v in settings.get("images", {}).items() if k not in CHOOSABLE},
        **{k: v for k, v in images.items() if v},
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
    """Browsers don't keep a chosen file when the page comes back with errors, so
    say so next to each slot that had one (#271)."""
    if not form.errors:
        return
    for slot, modes in CHOOSABLE.items():
        for mode in modes:
            name = image_field_name(slot, mode)
            value = form.cleaned_data.get(name) or {}
            if value.get("clean") and name not in form.errors:
                form.add_error(name, CHOOSE_AGAIN)


def save_images(form, theme):
    """After the theme is saved: store new uploads and choose them, and save edited
    alt text. A new upload in a slot replaces the choice made in the list."""
    images = theme.settings.get("images", {})
    assets = {a.pk: a for a in theme.assets.all()}
    changed = False
    for slot, modes in CHOOSABLE.items():
        for mode in modes:
            value = form.cleaned_data.get(image_field_name(slot, mode)) or {}
            alt = value.get("alt")
            if value.get("clean"):
                asset = store_asset(theme, slot, mode, value["clean"], alt or "")
                images.setdefault(slot, {})[mode] = asset.pk
                changed = True
            elif value.get("choice") in assets and alt is not None:
                asset = assets[value["choice"]]
                if asset.alt_text != alt:
                    asset.alt_text = alt
                    asset.save(update_fields=["alt_text"])
    if changed:
        theme.settings["images"] = images
        theme.save()
