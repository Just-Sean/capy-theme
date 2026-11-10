import json

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from .active import NotPublished, activate, get_active_theme
from .catalogue import get_builtin_themes
from .models import Theme, ThemeRevision
from .publishing import NothingToPublish, publish
from .stylesheet import stylesheet_url


def _base_choices(scheme):
    return [(theme.name, theme.name) for theme in get_builtin_themes() if theme.scheme == scheme]


class ThemeForm(forms.ModelForm):
    """The theme edit form.

    Only light themes are offered as the light base and dark themes as the dark
    base. Values stored in `settings` (site name, tagline, logo alt text) get
    their own fields here and are written back into `settings` on save.
    """

    light_base = forms.ChoiceField()
    dark_base = forms.ChoiceField()
    site_name = forms.CharField(
        required=False,
        max_length=100,
        help_text="Shown in headers, and instead of the logo if there's none.",
    )
    tagline = forms.CharField(
        required=False, max_length=200, help_text="A short line describing the site."
    )
    logo_alt = forms.CharField(
        required=False,
        max_length=200,
        label="Logo alt text",
        help_text="Describes the logo for screen readers. Leave blank to use the site name.",
    )

    # Form fields stored as keys in Theme.settings.
    SETTINGS_FIELDS = ["site_name", "tagline", "logo_alt"]

    class Meta:
        model = Theme
        fields = ["name", "slug", "light_base", "dark_base", "logo"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Built per form, so a change to CAPY_THEME_BUILTIN_THEMES shows immediately.
        for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
            self.fields[field].choices = _base_choices(scheme)
            self.fields[field].help_text = Theme._meta.get_field(field).help_text
            self.fields[field].initial = Theme._meta.get_field(field).default
        for field in self.SETTINGS_FIELDS:
            self.fields[field].initial = self.instance.settings.get(field, "")

    def clean(self):
        cleaned = super().clean()
        settings = dict(self.instance.settings)
        for field in self.SETTINGS_FIELDS:
            value = cleaned.get(field, "").strip()
            if value:
                settings[field] = value
            else:
                settings.pop(field, None)
        self.instance.settings = settings
        return cleaned


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
        "is_active",
        "live_revision_number",
        "unpublished_changes",
        "base_changed_in_daisyui",
        "updated_at",
    ]
    actions = ["activate_theme"]
    list_filter = ["light_base", "dark_base"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = ["publish_status", "settings_json", "public_id", "created_at", "updated_at"]
    fieldsets = [
        (None, {"fields": ["name", "slug"]}),
        ("Publishing", {"fields": ["publish_status"]}),
        ("Branding", {"fields": ["site_name", "tagline", "logo", "logo_alt"]}),
        ("Base themes", {"fields": ["light_base", "dark_base"]}),
        ("Overrides", {"fields": ["settings_json"]}),
        ("Details", {"fields": ["public_id", "created_at", "updated_at"]}),
    ]
    inlines = [ThemeRevisionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("live_revision")

    @admin.display(description="Stored settings")
    def settings_json(self, theme):
        """The draft's `settings` as JSON, read-only. Edited through the fields above."""
        return format_html("<pre>{}</pre>", json.dumps(theme.settings, indent=2, sort_keys=True))

    @admin.display(boolean=True, description="Active")
    def is_active(self, theme):
        active = get_active_theme()
        return active is not None and active.pk == theme.pk

    @admin.action(description="Activate the selected theme (make it the site's theme)")
    def activate_theme(self, request, queryset):
        # Anyone who can edit themes can activate for now; 1.9 adds a separate permission.
        if not self.has_change_permission(request):
            raise PermissionDenied
        if queryset.count() != 1:
            messages.error(request, "Select exactly one theme to activate.")
            return
        theme = queryset.select_related("live_revision").get()
        try:
            activate(theme)
        except NotPublished as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"“{theme}” is now the active theme.")

    @admin.display(description="Live revision", ordering="live_revision__number")
    def live_revision_number(self, theme):
        return theme.live_revision.number if theme.live_revision else "—"

    @admin.display(boolean=True, description="Unpublished changes")
    def unpublished_changes(self, theme):
        return theme.has_unpublished_changes

    @admin.display(boolean=True, description="Base changed in daisyUI")
    def base_changed_in_daisyui(self, theme):
        return bool(theme.base_changes())

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
        status = format_html(
            'Live: revision {} (published {} by {}). {} <a href="{}" target="_blank">'
            "View its stylesheet</a>",
            live.number,
            live.published_at.strftime("%Y-%m-%d %H:%M"),
            live.published_by or "unknown",
            changes,
            stylesheet_url(live),
        )
        for note in theme.base_changes():
            status += format_html('<p class="errornote">{}</p>', note)
        return status

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
            except IntegrityError:
                # Someone else published this theme at the same moment and took
                # the next revision number. Nothing was saved for this request.
                messages.warning(
                    request,
                    "Someone else just published this theme, so yours wasn't saved. "
                    "Check the live revision below, then publish again if needed.",
                )
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
