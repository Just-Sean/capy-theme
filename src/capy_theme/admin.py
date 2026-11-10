from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .catalogue import get_builtin_themes
from .models import Theme, ThemeRevision
from .publishing import NothingToPublish, publish


def _base_choices(scheme):
    return [(theme.name, theme.name) for theme in get_builtin_themes() if theme.scheme == scheme]


class ThemeForm(forms.ModelForm):
    """Offers only light themes as the light base and dark themes as the dark base."""

    light_base = forms.ChoiceField()
    dark_base = forms.ChoiceField()

    class Meta:
        model = Theme
        fields = ["name", "slug", "light_base", "dark_base", "settings"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Built per form, so a change to CAPY_THEME_BUILTIN_THEMES shows immediately.
        for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
            self.fields[field].choices = _base_choices(scheme)
            self.fields[field].help_text = Theme._meta.get_field(field).help_text
            self.fields[field].initial = Theme._meta.get_field(field).default


class PublishForm(forms.Form):
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "cols": 60}),
        help_text="Optional: what changed or why, for the history.",
    )


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


@admin.register(Theme)
class ThemeAdmin(admin.ModelAdmin):
    form = ThemeForm
    change_form_template = "capy_theme/admin/theme_change_form.html"
    list_display = [
        "name",
        "slug",
        "light_base",
        "dark_base",
        "live_revision_number",
        "unpublished_changes",
        "updated_at",
    ]
    list_filter = ["light_base", "dark_base"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["publish_status", "public_id", "created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["name", "slug"]}),
        ("Publishing", {"fields": ["publish_status"]}),
        ("Base themes", {"fields": ["light_base", "dark_base"]}),
        ("Overrides", {"fields": ["settings"]}),
        ("Details", {"fields": ["public_id", "created_at", "updated_at"]}),
    ]
    inlines = [ThemeRevisionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("live_revision")

    @admin.display(description="Live revision", ordering="live_revision__number")
    def live_revision_number(self, theme):
        return theme.live_revision.number if theme.live_revision else "—"

    @admin.display(boolean=True, description="Unpublished changes")
    def unpublished_changes(self, theme):
        return theme.has_unpublished_changes

    @admin.display(description="Status")
    def publish_status(self, theme):
        if theme.pk is None:
            return "Not saved yet. Save the theme, then publish it."
        live = theme.live_revision
        if live is None:
            return "Never published. Pages won't use this theme until it's published."
        changes = (
            "The draft has unpublished changes."
            if theme.has_unpublished_changes
            else "The draft matches the live revision."
        )
        return format_html(
            "Live: revision {} (published {} by {}). {}",
            live.number,
            live.published_at.strftime("%Y-%m-%d %H:%M"),
            live.published_by or "unknown",
            changes,
        )

    # The Publish page

    def get_urls(self):
        return [
            path(
                "<path:object_id>/publish/",
                self.admin_site.admin_view(self.publish_view),
                name="capy_theme_theme_publish",
            ),
            *super().get_urls(),
        ]

    def publish_view(self, request, object_id):
        theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=object_id)
        # Anyone who can edit themes can publish for now; 1.9 adds a separate permission.
        if not self.has_change_permission(request, theme):
            raise PermissionDenied
        change_url = reverse("admin:capy_theme_theme_change", args=[theme.pk])

        form = PublishForm(request.POST or None)
        if request.method == "POST" and form.is_valid():
            try:
                revision = publish(theme, user=request.user, note=form.cleaned_data["note"])
            except NothingToPublish as error:
                messages.warning(request, str(error))
            except ValidationError as error:
                messages.error(request, "Can't publish: " + " ".join(error.messages))
            else:
                messages.success(request, f"Published “{theme}” as revision {revision.number}.")
            return redirect(change_url)

        context = {
            **self.admin_site.each_context(request),
            "title": f"Publish “{theme}”",
            "opts": self.opts,
            "theme": theme,
            "form": form,
            "change_url": change_url,
            "has_changes": theme.has_unpublished_changes,
        }
        return TemplateResponse(request, "capy_theme/admin/publish_theme.html", context)
