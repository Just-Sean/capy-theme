"""A theme's uploaded images (ThemeAsset) and their generated copies (ThemeAssetVariant)."""

from django.db import models

from .slots import MODES, SLOT_CHOICES


def asset_path(asset, filename):
    return f"capy_theme/assets/{asset.slot}/{filename}"


class ThemeAsset(models.Model):
    """An image a theme uses: a logo, the icon, the sharing image or a background.

    Never edited after upload: a new image is a new asset, so older revisions keep
    showing theirs. Generated sizes and formats are in ThemeAssetVariant.
    """

    theme = models.ForeignKey("capy_theme.Theme", on_delete=models.CASCADE, related_name="assets")
    slot = models.CharField(max_length=40, choices=SLOT_CHOICES)
    mode = models.CharField(max_length=10, choices=MODES, default="light")
    original = models.FileField(upload_to=asset_path)
    alt_text = models.CharField(max_length=200, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    size = models.PositiveIntegerField(default=0, help_text="File size in bytes.")
    content_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["theme", "slot", "mode", "-created_at"]

    def __str__(self):
        return f"{self.theme} {self.slot} ({self.mode})"


def variant_path(variant, filename):
    return f"capy_theme/assets/{variant.asset.slot}/variants/{filename}"


class ThemeAssetVariant(models.Model):
    """One generated size or format of an asset (e.g. a 320 px WebP of the logo)."""

    asset = models.ForeignKey(ThemeAsset, on_delete=models.CASCADE, related_name="variants")
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    format = models.CharField(max_length=10, help_text="png, webp, avif, ico or svg.")
    purpose = models.CharField(max_length=40, blank=True, help_text="e.g. favicon-32 or 2x.")
    file = models.FileField(upload_to=variant_path)

    class Meta:
        ordering = ["asset", "format", "width"]

    def __str__(self):
        return f"{self.asset} {self.width}px {self.format}"
