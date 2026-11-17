"""The theme edit page's lists: Media (uploaded images) and published revisions."""

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from ..images.assets import where_used
from ..images.models import ThemeAsset
from ..models import ThemeRevision


class ThemeRevisionInline(admin.TabularInline):
    """The theme's published revisions. They can be viewed, never edited or deleted."""

    model = ThemeRevision
    classes = ["collapse"]  # foldable like every section; starts folded
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


class ThemeAssetFormSet(forms.BaseInlineFormSet):
    """Refuses to delete an image that's in use (#271)."""

    def clean(self):
        super().clean()
        for form in self.deleted_forms:
            asset = form.instance
            if asset.pk is None:
                continue
            uses = where_used(self.instance, self.instance.settings, asset)
            if uses:
                # Not deleted after all, and an error on the row: Django skips errors on
                # rows being deleted, and an error on a row shows the Media list unfolded.
                form.cleaned_data["DELETE"] = False
                form.add_error(
                    None,
                    f"This image can't be deleted: it's used as {' and '.join(uses)}. "
                    "Upload a new image for that slot, or set it to None, and save; "
                    "then delete this one.",
                )


class ThemeAssetInline(admin.TabularInline):
    """Media: every image uploaded for the theme (#271). Images are uploaded and
    chosen where they're used (Logos, Icon, Backgrounds, Sharing image); here their
    alt text can be edited, and unused ones deleted. The image itself never
    changes, so older revisions keep showing theirs."""

    model = ThemeAsset
    formset = ThemeAssetFormSet
    classes = ["collapse"]  # foldable like every section; starts folded
    extra = 0
    fields = ["preview", "slot", "mode", "alt_text", "details", "used"]
    readonly_fields = ["preview", "slot", "mode", "details", "used"]
    verbose_name = "image"
    verbose_name_plural = "Media"

    # Managing a theme's images is part of editing the theme.
    def has_add_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("theme__live_revision")

    def has_change_permission(self, request, obj=None):
        return request.user.has_perm("capy_theme.change_theme")

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("capy_theme.change_theme")

    @admin.display(description="Preview")
    def preview(self, asset):
        if not asset.pk:
            return ""
        return format_html(
            '<img class="capy-media-preview" src="{}" alt="{}">',
            asset.original.url,
            asset.alt_text,
        )

    @admin.display(description="Details")
    def details(self, asset):
        if not asset.pk:
            return ""
        name = asset.original.name.rsplit("/", 1)[-1]
        return (
            f"{name}: {asset.width} × {asset.height}, {asset.size // 1024} KB, {asset.content_type}"
        )

    @admin.display(description="Used as")
    def used(self, asset):
        if not asset.pk:
            return ""
        uses = where_used(asset.theme, asset.theme.settings, asset)
        return "; ".join(uses) if uses else "Not used: can be deleted"
