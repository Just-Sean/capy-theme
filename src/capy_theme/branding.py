"""The published branding (site name, tagline, logo) of a revision."""

from django.core.files.storage import default_storage


def branding(revision):
    """Return the revision's site name, tagline, logo URL and logo alt text.

    Everything comes from the published snapshot, never the draft. The logo's
    alt text falls back to the site name.
    """
    settings = revision.snapshot.get("settings", {})
    site_name = settings.get("site_name", "")
    logo = revision.snapshot.get("logo", "")
    return {
        "site_name": site_name,
        "tagline": settings.get("tagline", ""),
        "logo_url": default_storage.url(logo) if logo else "",
        "logo_alt": settings.get("logo_alt") or site_name,
    }
