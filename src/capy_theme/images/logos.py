"""Logo slots: which image each slot and mode uses, with fallbacks."""

LOGO_SLOTS = (
    "logo_main",
    "logo_stacked",
    "logo_mark",
    "logo_wordmark",
    "logo_email",
    "logo_print",
)


# When a slot has no image, the slot it falls back to.
FALLBACK = {slot: "logo_main" for slot in LOGO_SLOTS if slot != "logo_main"}


# Slots shown in page headers: these get smaller copies and the header height.
HEADER_SLOTS = ("logo_main", "logo_stacked", "logo_mark", "logo_wordmark")


# Header logo heights (px). Phones are windows up to MOBILE px wide.
HEIGHTS = {
    "header_height": ("Header logo height (px)", 40),
    "header_height_mobile": ("Header logo height on phones (px)", 32),
}


MOBILE = 640


def snapshot_images(theme, settings):
    """The chosen images, as published: {slot: {mode: {file, width, ...}}}."""
    from .models import ThemeAsset

    chosen = settings.get("images", {})
    ids = {pk for modes in chosen.values() for pk in modes.values()}
    if not ids or theme.pk is None:
        return {}
    assets = {
        a.pk: a
        for a in ThemeAsset.objects.filter(theme=theme, pk__in=ids).prefetch_related("variants")
    }
    images = {}
    for slot, modes in chosen.items():
        for mode, pk in modes.items():
            asset = assets.get(pk)
            if asset is None:
                continue
            images.setdefault(slot, {})[mode] = {
                "file": asset.original.name,
                "width": asset.width,
                "height": asset.height,
                "content_type": asset.content_type,
                "alt": asset.alt_text,
                "variants": [
                    {
                        "file": v.file.name,
                        "width": v.width,
                        "format": v.format,
                        **({"purpose": v.purpose} if v.purpose else {}),
                    }
                    for v in asset.variants.all()
                ],
            }
    return images


def resolve(snapshot, slot, mode):
    """The published image for a slot and mode, following fallbacks, or None.

    Dark mode uses the slot's light image if it has no dark one. A slot with no
    image uses its fallback slot (e.g. the stacked logo falls back to the main one).
    """
    images = snapshot.get("images", {})
    is_logo = slot in LOGO_SLOTS
    while slot:
        entry = images.get(slot, {})
        for choice in (mode, "light") if mode == "dark" else ("light",):
            if choice in entry:
                return entry[choice]
        slot = FALLBACK.get(slot)
    legacy = snapshot.get("logo")  # revisions published before logo slots
    if legacy and is_logo:
        return {"file": legacy, "width": 0, "height": 0, "content_type": "", "alt": ""}
    return None
