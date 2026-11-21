"""The Components view's images section: every image and icon the theme produces."""


def images(theme):
    """Data for the Components view's images section, from the saved draft.

    The icons come from the published revision, because they're made when
    publishing.

    {"logos": [...], "backgrounds": [...], "icons": [...], "icon_preview": {...},
    "sharing": {...}}. Each logo says which image it shows and why (its own, or the
    main logo it falls back to).
    """
    from ..images.icons import FILES, icon_urls
    from ..images.logos import FALLBACK, HEADER_SLOTS, LOGO_SLOTS, resolve
    from ..images.sharing import SIZE, sharing_image
    from ..images.slots import SLOTS
    from ..storage import theme_storage

    snapshot = theme.snapshot()
    settings = snapshot.get("settings", {})
    chosen = snapshot.get("images", {})
    url = theme_storage().url
    logos = []
    for slot in LOGO_SLOTS:
        image = resolve(snapshot, slot)
        if slot in chosen:
            source = "Its own image"
        elif FALLBACK.get(slot) and image:
            source = f"Empty: falls back to the {SLOTS[FALLBACK[slot]][0].lower()}"
        elif image:
            source = "From before logo slots"
        else:
            source = "Empty: shows the site name"
        # Email and print logos are always the plain file (see logos.logo_html).
        variants = image.get("variants", []) if image and slot in HEADER_SLOTS else []
        logos.append(
            {
                "slot": slot,
                "label": SLOTS[slot][0],
                "header": slot in HEADER_SLOTS,
                "url": url(image["file"]) if image else "",
                "width": image["width"] if image else 0,
                "height": image["height"] if image else 0,
                "alt": (image or {}).get("alt") or settings.get("site_name", ""),
                "source": source,
                "formats": sorted({v["format"].upper() for v in variants}),
                "widths": sorted({v["width"] for v in variants}),
            }
        )
    backgrounds = [
        {
            "label": SLOTS[slot][0],
            "class": f"capy-bg-{slot.removeprefix('background_')}",
            "set": resolve(snapshot, slot) is not None,
        }
        for slot in ("background_login", "background_pattern")
    ]
    urls = icon_urls(theme.live_revision.snapshot) if theme.live_revision else {}
    icons = (
        [
            {"name": name, "url": urls[name], "size": size, "label": text}
            for name, (size, text) in FILES.items()
        ]
        if urls
        else []
    )
    # The icon image chosen in the draft, for a live preview of its settings.
    icon_settings = theme.settings.get("icon", {})
    icon_preview = {
        "asset": theme.settings.get("images", {}).get("icon"),
        "background": icon_settings.get("background", ""),
        "padding": icon_settings.get("padding", 0),
    }
    share = sharing_image(snapshot)
    return {
        "logos": logos,
        "backgrounds": backgrounds,
        "icons": icons,
        "icon_preview": icon_preview,
        "sharing": {
            "image": url(share["file"]) if share else "",
            "alt": share["alt"] if share else "",
            "size": SIZE,
        },
    }
