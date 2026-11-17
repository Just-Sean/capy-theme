"""Storing checked images as a theme's assets, and which assets are in use."""

from .slots import SLOTS

ALT_MAX = 200


def store_asset(theme, slot, mode, clean, alt_text=""):
    """Store an image already checked by uploads.prepare_image as a new ThemeAsset.

    Makes its smaller copies (header logos) and the 1200 × 630 copy (sharing
    image), like every upload. Existing assets are never changed.
    """
    from .models import ThemeAsset
    from .sharing import make_sharing_image
    from .variants import make_variants

    asset = ThemeAsset(
        theme=theme,
        slot=slot,
        mode=mode,
        alt_text=alt_text.strip()[:ALT_MAX],
        width=clean["width"],
        height=clean["height"],
        size=clean["size"],
        content_type=clean["content_type"],
    )
    asset.original.save(clean["file"].name, clean["file"], save=False)
    asset.save()
    make_variants(asset)
    if slot == "social":
        make_sharing_image(asset)
    return asset


def where_used(theme, settings, asset):
    """Where an asset is in use, as short descriptions; [] if it's free to delete.

    In use means chosen in the draft (`settings`, which may be unsaved) or shown
    by the live revision.
    """
    uses = []
    for slot, modes in settings.get("images", {}).items():
        for mode, pk in modes.items():
            if pk == asset.pk:
                uses.append(f"the draft's {_place(slot, mode)}")
    live = theme.live_revision.snapshot if theme.live_revision_id else {}
    for slot, modes in live.get("images", {}).items():
        for mode, image in modes.items():
            if image.get("file") == asset.original.name:
                uses.append(f"the published theme's {_place(slot, mode)}")
    return uses


def _place(slot, mode):
    label = SLOTS.get(slot, (slot,))[0].lower()
    return label if slot == "social" else f"{label} ({mode})"


def asset_data(asset):
    """An asset as JSON-ready data (for the editor)."""
    return {
        "id": asset.pk,
        "slot": asset.slot,
        "slot_label": SLOTS.get(asset.slot, (asset.slot,))[0],
        "mode": asset.mode,
        "url": asset.original.url,
        "name": asset.original.name.rsplit("/", 1)[-1],
        "alt_text": asset.alt_text,
        "width": asset.width,
        "height": asset.height,
        "size": asset.size,
        "content_type": asset.content_type,
    }
