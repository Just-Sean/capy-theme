"""The published branding (site name, tagline, logo) of a revision."""

from django.core.files.storage import default_storage

from ..images.logos import resolve


def branding(revision):
    """Return the revision's site name, tagline, logo URL and logo alt text.

    Everything comes from the published snapshot, never the draft. The logo is
    the main logo's light version; its alt text falls back to the theme's logo
    alt text, then the site name.
    """
    settings = revision.snapshot.get("settings", {})
    site_name = settings.get("site_name", "")
    logo = resolve(revision.snapshot, "logo_main", "light")
    return {
        "site_name": site_name,
        "tagline": settings.get("tagline", ""),
        "logo_url": default_storage.url(logo["file"]) if logo else "",
        "logo_alt": (logo or {}).get("alt") or settings.get("logo_alt") or site_name,
    }
