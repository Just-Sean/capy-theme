"""The Components view's images section: every image and icon the theme produces."""

from ..colors.names import SCHEMES


def images(theme):
    """Data for the Components view's images section, per mode, from the saved draft.

    The icons come from the published revision, because they're made when
    publishing.

    {mode: {"logos": [...], "icons": [...], "backgrounds": [...]}, plus
    "sharing" (the sharing image)}.
    Each logo says which image it shows and why (its own, the light one, or the
    main logo it falls back to).
    """
    from django.core.files.storage import default_storage

    from ..images.icons import FILES, icon_urls
    from ..images.logos import FALLBACK, HEADER_SLOTS, LOGO_SLOTS, resolve
    from ..images.sharing import SIZE, sharing_image
    from ..images.slots import SLOTS

    snapshot = theme.snapshot()
    settings = snapshot.get("settings", {})
    chosen = snapshot.get("images", {})
    url = default_storage.url
    result = {}
    for mode in SCHEMES:
        logos = []
        for slot in LOGO_SLOTS:
            # Email and print logos always use the light version (see logos.logo_html).
            header = slot in HEADER_SLOTS
            image = resolve(snapshot, slot, mode if header else "light")
            own = chosen.get(slot, {})
            if not header and mode == "dark" and image:
                source = "Always the light version (emails and print have no dark mode)"
            elif mode in own:
                source = "Its own image"
            elif "light" in own:
                source = "No dark version: uses the light one"
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
                "set": resolve(snapshot, slot, mode) is not None,
            }
            for slot in ("background_login", "background_pattern")
        ]
        result[mode] = {"logos": logos, "backgrounds": backgrounds}
    urls = icon_urls(theme.live_revision.snapshot) if theme.live_revision else {}
    result["icons"] = (
        [
            {"name": name, "url": urls[name], "size": size, "label": text}
            for name, (size, text) in FILES.items()
        ]
        if urls
        else []
    )
    share = sharing_image(snapshot)
    result["sharing"] = {
        "image": url(share["file"]) if share else "",
        "alt": share["alt"] if share else "",
        "size": SIZE,
    }
    return result
