"""The theme edit page's lists: Media (uploaded images) and published revisions."""

from django import forms
from django.contrib import admin
from django.utils.html import format_html

from ..images.assets import refusal, revisions_of, where_used
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

    def _should_delete_form(self, form):
        """A row marked for deletion whose image is in use isn't deleted: it gets an
        error instead. Checked here, where Django decides which rows are deleted, so
        the error counts like any other row error (the page says so at the top and
        the Media list is shown unfolded)."""
        if not super()._should_delete_form(form) or form.instance.pk is None:
            return False
        if not hasattr(form, "capy_refusal"):
            if not hasattr(self, "capy_revisions"):
                self.capy_revisions = revisions_of(self.instance)
            form.capy_refusal = refusal(
                self.instance, self.instance.settings, form.instance, self.capy_revisions
            )
            if form.capy_refusal:
                form.add_error(None, form.capy_refusal)
                _untick(form)
        return not form.capy_refusal


def _untick(form):
    """Show the row's Delete box unticked when the page comes back."""
    data = form.data.copy()
    data.pop(form.add_prefix("DELETE"), None)
    form.data = data


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
        if getattr(self, "capy_revisions", None) is None:  # once per page, not per row
            self.capy_revisions = revisions_of(asset.theme)
        uses = where_used(asset.theme, asset.theme.settings, asset, self.capy_revisions)
        return "; ".join(uses) if uses else "Not used: can be deleted"
