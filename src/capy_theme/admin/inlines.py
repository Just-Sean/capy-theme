"""The theme edit page's lists: uploaded images and published revisions."""

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.utils.html import format_html

from ..images.models import ThemeAsset
from ..images.uploads import prepare_image
from ..models import ThemeRevision


class ThemeRevisionInline(admin.TabularInline):
    """The theme's published revisions. They can be viewed, never edited or deleted."""

    model = ThemeRevision
    fields = ["number", "published_at", "published_by", "note", "is_live"]
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = False
    verbose_name = "published revision"
    verbose_name_plural = "Published revisions"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(boolean=True, description="Live")
    def is_live(self, revision):
        return revision.theme.live_revision_id == revision.pk


class ThemeAssetForm(forms.ModelForm):
    """Upload an image: checked by content, size-limited per slot, metadata removed."""

    class Meta:
        model = ThemeAsset
        fields = ["slot", "mode", "original", "alt_text"]
        labels = {"original": "Image"}
        help_texts = {
            "original": "PNG, JPEG, WebP, GIF or SVG. Location and camera details are removed; "
            "SVGs are cleaned of scripts and links."
        }

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get("original")
        slot = cleaned.get("slot")
        if upload and slot and self.instance.pk is None:
            try:
                upload.seek(0)
                self.clean_image = prepare_image(upload.read(), upload.name, slot)
            except ValidationError as error:
                self.add_error("original", error)
        return cleaned

    def save(self, commit=True):
        asset = super().save(commit=False)
        clean = getattr(self, "clean_image", None)
        if clean:
            asset.original = clean["file"]
            asset.width, asset.height = clean["width"], clean["height"]
            asset.size, asset.content_type = clean["size"], clean["content_type"]
        if commit:
            asset.save()
        return asset


class ThemeAssetInline(admin.TabularInline):
    """A theme's images. An image is never changed once uploaded: to replace one,
    upload a new image (and delete the old one if nothing needs it)."""

    model = ThemeAsset
    form = ThemeAssetForm
    extra = 0
    fields = ["preview", "slot", "mode", "original", "alt_text", "details"]
    readonly_fields = ["preview", "details"]
    verbose_name = "image"
    verbose_name_plural = "Images"

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Preview")
    def preview(self, asset):
        if not asset.pk:
            return ""
        return format_html(
            '<img src="{}" alt="{}" style="max-width: 120px; max-height: 60px">',
            asset.original.url,
            asset.alt_text,
        )

    @admin.display(description="Details")
    def details(self, asset):
        if not asset.pk:
            return ""
        return f"{asset.width} × {asset.height}, {asset.size // 1024} KB, {asset.content_type}"
