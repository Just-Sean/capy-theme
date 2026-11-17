"""Storing checked images as a theme's assets, and which assets are in use."""

from .slots import SLOT_MODES, SLOTS

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


def revisions_of(theme):
    """(number, chosen images, is live) for each of the theme's revisions, newest
    first. Only the images part of each snapshot is read. Load once and pass to
    where_used / refusal for many images."""
    if theme.pk is None:
        return []
    rows = theme.revisions.order_by("-number").values_list(
        "pk", "number", "snapshot__settings__images"
    )
    return [(number, images or {}, pk == theme.live_revision_id) for pk, number, images in rows]


def _uses(theme, settings, asset, revisions):
    """(kinds, descriptions) for where an asset is chosen: kinds holds "draft",
    "live" and "earlier". Earlier revisions are counted, not listed one by one.
    Choices a slot can't have (e.g. an old dark email logo) don't count."""
    kinds, texts = set(), []
    for place in _places(settings.get("images", {}), asset):
        kinds.add("draft")
        texts.append(f"the draft's {place}")
    earlier = 0
    for _number, images, live in revisions if revisions is not None else revisions_of(theme):
        places = _places(images, asset)
        if places and live:
            kinds.add("live")
            texts.extend(f"the published theme's {place}" for place in places)
        elif places:
            earlier += 1
    if earlier:
        kinds.add("earlier")
        texts.append(f"{earlier} earlier revision{'s' if earlier > 1 else ''}")
    return kinds, texts


def _places(images, asset):
    if not isinstance(images, dict):
        return []
    return [
        _place(slot, mode)
        for slot, modes in images.items()
        if isinstance(modes, dict)
        for mode, pk in modes.items()
        if pk == asset.pk and mode in SLOT_MODES.get(slot, ())
    ]


def where_used(theme, settings, asset, revisions=None):
    """Where an asset is in use, as short descriptions; [] if it's free to delete.

    In use means chosen in the draft (`settings`, which may be unsaved) or in any of
    the theme's revisions: restoring a revision needs its images (#271).
    """
    return _uses(theme, settings, asset, revisions)[1]


def refusal(theme, settings, asset, revisions=None):
    """Why an asset can't be deleted and what to do instead, or "" if it can be."""
    kinds, texts = _uses(theme, settings, asset, revisions)
    if not texts:
        return ""
    why = f"This image can't be deleted: it's used as {'; '.join(texts)}."
    if kinds & {"live", "earlier"}:
        # Published revisions are kept for good, so their images are too.
        return (
            f"{why} Published versions of the theme keep their images, so that restoring "
            "one keeps working: once an image has been published, it stays in Media."
        )
    return (
        f"{why} To delete it, choose another image for that slot (or None; for dark "
        "mode, Same as light) and save; then delete it."
    )


def _place(slot, mode):
    label = SLOTS.get(slot, (slot,))[0].lower()
    return label if len(SLOT_MODES.get(slot, ())) < 2 else f"{label} ({mode})"


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
