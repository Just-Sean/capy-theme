"""The theme form's image choices: logo slots, icon, sharing image, backgrounds."""

from django import forms

from ..images.icons import SETTINGS as ICON_SETTINGS
from ..images.logos import HEIGHTS, LOGO_SLOTS
from ..images.slots import SLOTS


def image_field_name(slot, mode):
    return f"image_{slot}_{mode}"


# The image slots with a choice in the form, and their modes. The sharing image
# has no dark version: link previews have no dark mode.
CHOOSABLE = {
    **{slot: ("light", "dark") for slot in LOGO_SLOTS},
    "icon": ("light", "dark"),
    "social": ("light",),
    "background_login": ("light", "dark"),
    "background_pattern": ("light", "dark"),
}


def add_fields(form_class):
    for slot, modes in CHOOSABLE.items():
        for mode in modes:
            name = image_field_name(slot, mode)
            form_class.base_fields[name] = form_class.declared_fields[name] = forms.ChoiceField(
                required=False,
                label=SLOTS[slot][0] if len(modes) == 1 else f"{SLOTS[slot][0]} ({mode})",
                help_text=SLOTS[slot][3]
                + (" Leave dark empty to use the light one." if mode == "dark" else ""),
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
            error_messages={"invalid": "Use a hex colour like #ffffff."},
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
        for mode in modes:
            choices = [("", "None (use the fallback)")] + [
                (str(a.pk), f"{a.original.name.rsplit('/', 1)[-1]} ({a.width} × {a.height})")
                for a in assets
                if a.slot == slot
            ]
            field = form.fields[image_field_name(slot, mode)]
            field.choices = choices
            field.initial = str(chosen.get(slot, {}).get(mode, ""))
    heights = form.instance.settings.get("logo", {})
    for name in HEIGHTS:
        form.fields[f"logo_{name}"].initial = heights.get(name)
    icon = form.instance.settings.get("icon", {})
    for name in ICON_SETTINGS:
        form.fields[f"icon_{name}"].initial = icon.get(name)


def clean(form, cleaned, settings):
    images = {
        slot: {
            mode: int(cleaned[image_field_name(slot, mode)])
            for mode in modes
            if cleaned.get(image_field_name(slot, mode))
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
