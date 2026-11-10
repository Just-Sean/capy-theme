"""The theme list and edit page in the admin."""

import json

from django.contrib import admin, messages
from django.utils.html import format_html, format_html_join

from ..colors.names import SCHEMES
from ..colors.values import contrast_report, draft_values
from ..css.stylesheet import stylesheet_url
from ..editor.access import can_edit
from ..models import Theme
from ..themes.active import NotPublished, activate, get_active_theme
from .fieldsets import THEME_FIELDSETS
from .form_colors import _pair
from .inlines import ThemeAssetInline, ThemeRevisionInline
from .publish_pages import PublishPagesMixin
from .theme_form import ThemeForm


def edit_live_url(theme_id):
    """Where "Edit live" opens the editor: the site's home page, with ?edit=<id>."""
    return f"/?edit={theme_id}"


@admin.register(Theme)
class ThemeAdmin(PublishPagesMixin, admin.ModelAdmin):
    form = ThemeForm
    change_form_template = "capy_theme/admin/theme_change_form.html"
    list_display = [
        "name",
        "slug",
        "light_base",
        "dark_base",
        "is_active",
        "offered_to_visitors",
        "live_revision_number",
        "unpublished_changes",
        "base_changed_in_daisyui",
        "updated_at",
    ]
    actions = ["activate_theme"]
    list_filter = ["light_base", "dark_base"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ["name"]}
    readonly_fields = [
        "publish_status",
        "contrast_table",
        "settings_json",
        "public_id",
        "created_at",
        "updated_at",
    ]
    fieldsets = THEME_FIELDSETS
    inlines = [ThemeAssetInline, ThemeRevisionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("live_revision")

    @admin.display(description="WCAG contrast (saved draft)")
    def contrast_table(self, theme):
        """Every colour pair's contrast rating, for light and dark. Warnings only."""
        if theme.pk is None:
            return "Save the theme to see its contrast ratings."
        rows = []
        for scheme in SCHEMES:
            values = draft_values(theme, scheme)
            if not values:
                continue
            for entry in contrast_report(values):
                rows.append(
                    format_html(
                        "<tr><td>{}</td><td>{}</td><td>{}:1</td><td>{}</td></tr>",
                        scheme.capitalize(),
                        _pair(entry),
                        entry["ratio"],
                        "⚠ fails AA" if entry["rating"] == "fail" else entry["rating"],
                    )
                )
        return format_html(
            "<table><thead><tr><th>Mode</th><th>Pair</th><th>Ratio</th><th>Rating</th></tr>"
            "</thead><tbody>{}</tbody></table>"
            "<p>AA needs 4.5:1 and AAA 7:1 for normal text. These are warnings: saving and "
            "publishing still work.</p>",
            format_html_join("", "{}", ((row,) for row in rows)),
        )

    @admin.display(description="Stored settings")
    def settings_json(self, theme):
        """The draft's `settings` as JSON, read-only. Edited through the fields above."""
        return format_html("<pre>{}</pre>", json.dumps(theme.settings, indent=2, sort_keys=True))

    @admin.display(boolean=True, description="Active")
    def is_active(self, theme):
        active = get_active_theme()
        return active is not None and active.pk == theme.pk

    def has_publish_permission(self, request, obj=None):
        """Publishing, activating and (later) restoring need the publish_theme permission."""
        return request.user.has_perm("capy_theme.publish_theme")

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {
            **(extra_context or {}),
            "can_publish": self.has_publish_permission(request),
            "edit_live_url": edit_live_url(object_id) if can_edit(request.user) else None,
        }
        return super().change_view(request, object_id, form_url, extra_context)

    # Shown in the actions menu only to users with the publish_theme permission.
    @admin.action(
        description="Activate the selected theme (make it the site's theme)",
        permissions=["publish"],
    )
    def activate_theme(self, request, queryset):
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
