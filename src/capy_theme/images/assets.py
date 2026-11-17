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
    """(number, snapshot, is live) for each of the theme's revisions, newest first.
    Load once and pass to where_used / refusal for many images."""
    if theme.pk is None:
        return []
    return [
        (number, snapshot, pk == theme.live_revision_id)
        for pk, number, snapshot in theme.revisions.order_by("-number").values_list(
            "pk", "number", "snapshot"
        )
    ]


def _uses(theme, settings, asset, revisions):
    """[(kind, description)] for where an asset is chosen: kind is "draft", "live"
    or "revision". Choices a slot can't have (e.g. an old dark email logo) don't count."""
    uses = [("draft", f"the draft's {place}") for place in _places(settings, asset)]
    for number, snapshot, live in revisions if revisions is not None else revisions_of(theme):
        for place in _places(snapshot.get("settings", {}), asset):
            if live:
                uses.append(("live", f"the published theme's {place}"))
            else:
                uses.append(("revision", f"revision {number}'s {place}"))
    return uses


def _places(settings, asset):
    return [
        _place(slot, mode)
        for slot, modes in settings.get("images", {}).items()
        for mode, pk in modes.items()
        if pk == asset.pk and mode in SLOT_MODES.get(slot, ())
    ]


def where_used(theme, settings, asset, revisions=None):
    """Where an asset is in use, as short descriptions; [] if it's free to delete.

    In use means chosen in the draft (`settings`, which may be unsaved) or in any of
    the theme's revisions: restoring a revision needs its images (#271).
    """
    return [text for _kind, text in _uses(theme, settings, asset, revisions)]


def refusal(theme, settings, asset, revisions=None):
    """Why an asset can't be deleted and what to do instead, or "" if it can be."""
    uses = _uses(theme, settings, asset, revisions)
    if not uses:
        return ""
    kinds = {kind for kind, _text in uses}
    steps = []
    if kinds & {"draft", "live"}:
        steps.append(
            "To free it, choose another image for that slot (or None; for dark mode, "
            "Same as light) and save" + (", then publish." if "live" in kinds else ".")
        )
    if "revision" in kinds:
        steps.append(
            "An earlier revision uses it, and restoring that revision needs it, so it "
            "can't be deleted while that revision exists."
        )
    return (
        f"This image can't be deleted: it's used as {'; '.join(t for _k, t in uses)}. "
        + " ".join(steps)
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
