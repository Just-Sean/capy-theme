"""Link previews: the sharing image and the Open Graph and Twitter card tags.

When a link to the site is shared (in chat apps, social sites...), the preview
shows the page's title, description and image from these tags. The defaults
come from the theme; pages can override them (see {% theme_social_tags %}).
"""

import io
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils.html import format_html, format_html_join
from PIL import Image, ImageOps

SIZE = (1200, 630)  # what Facebook, LinkedIn, X and most chat apps show best
SETTINGS = {
    "description": (
        "Sharing description",
        "Shown under the title in link previews. Blank: the tagline.",
    ),
}


def make_sharing_image(asset):
    """Save the asset cropped to 1200 × 630 as a variant (purpose "social").

    Cropped from the centre to fill the whole size. Transparent parts are made
    white, since some sites show transparency as black.
    """
    from .models import ThemeAssetVariant

    with asset.original.open("rb") as file:
        image = Image.open(file)
        image.load()
    image = image.convert("RGBA")
    white = Image.new("RGBA", image.size, (255, 255, 255, 255))
    flat = Image.alpha_composite(white, image).convert("RGB")
    cropped = ImageOps.fit(flat, SIZE, Image.Resampling.LANCZOS)
    output = io.BytesIO()
    if asset.content_type == "image/jpeg":
        cropped.save(output, "JPEG", quality=88, optimize=True)
        fmt, extension = "jpeg", "jpg"
    else:
        cropped.save(output, "PNG", optimize=True)
        fmt, extension = "png", "png"
    variant = ThemeAssetVariant(
        asset=asset, width=SIZE[0], height=SIZE[1], format=fmt, purpose="social"
    )
    stem = Path(asset.original.name).stem
    variant.file.save(
        f"{stem}-{SIZE[0]}x{SIZE[1]}.{extension}", ContentFile(output.getvalue()), save=False
    )
    variant.save()


def sharing_image(snapshot):
    """The published sharing image: {"file", "width", "height", "alt"}, or None."""
    image = snapshot.get("images", {}).get("social", {}).get("light")
    if not image:
        return None
    for variant in image.get("variants", []):
        if variant.get("purpose") == "social":
            return {
                "file": variant["file"],
                "width": SIZE[0],
                "height": SIZE[1],
                "alt": image["alt"],
            }
    return None


def tags(request, snapshot, title=None, description=None, image=None, image_alt=None):
    """The Open Graph and Twitter card <meta> tags.

    `title`, `description` and `image` (a URL) override the theme's defaults
    (site name, sharing description or tagline, sharing image).
    """
    settings = snapshot.get("settings", {})
    site_name = settings.get("site_name", "")
    title = title or site_name
    description = (
        description or settings.get("social", {}).get("description") or settings.get("tagline")
    )
    absolute = request.build_absolute_uri if request is not None else (lambda url: url)
    width = height = None
    if image:
        image_url, alt = absolute(image), image_alt or ""
    else:
        default = sharing_image(snapshot)
        image_url = absolute(default_storage.url(default["file"])) if default else None
        alt = image_alt or (default["alt"] if default else "") or title
        if default:
            width, height = default["width"], default["height"]
    properties = [
        ("og:type", "website"),
        ("og:site_name", site_name),
        ("og:title", title),
        ("og:description", description),
        ("og:url", absolute(request.path) if request is not None else None),
        ("og:image", image_url),
        ("og:image:width", width),
        ("og:image:height", height),
        ("og:image:alt", alt if image_url else None),
    ]
    names = [
        ("twitter:card", "summary_large_image" if image_url else "summary"),
        ("twitter:title", title),
        ("twitter:description", description),
        ("twitter:image", image_url),
        ("twitter:image:alt", alt if image_url else None),
    ]
    return format_html(
        "{}{}",
        format_html_join(
            "",
            '<meta property="{}" content="{}">\n',
            ((key, value) for key, value in properties if value),
        ),
        format_html_join(
            "", '<meta name="{}" content="{}">\n', ((key, value) for key, value in names if value)
        ),
    )
