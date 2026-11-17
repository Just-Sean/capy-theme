"""Saving, publishing and activating a theme from one place (#273).

The theme page has Save draft, Save and publish, and Save, publish and activate
(with a status line and a note for the history); the theme list has Publish,
Publish and activate, and Activate buttons on each row. Publishing and activating
need the publish_theme permission. Activating makes a theme the site's theme for
every site that has no site theme of its own (themes.active.activate).
"""

from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html_join
from django.views.decorators.http import require_POST

from ..models import Theme
from ..themes.active import NotPublished, activate, get_active_theme
from ..themes.publishing import NOTHING_TO_PUBLISH, NothingToPublish, publish, publish_and_activate

# The theme page's buttons (names of the submit buttons) and the note box.
SAVE = "_capy_save"
PUBLISH = "_capy_publish"
PUBLISH_ACTIVATE = "_capy_publish_activate"
NOTE = "_capy_note"
NOTE_MAX = 2000

SIMULTANEOUS = (
    "Someone else just published this theme at the same moment, so yours wasn't "
    "published. Check its revisions, then publish again if needed."
)


def site_theme_id():
    """The id of the site's theme (for every site), or None."""
    theme = get_active_theme()
    return theme.pk if theme is not None else None


def publish_status(theme):
    """[(label, text)] for the theme page's status line."""
    if theme is None or theme.pk is None:
        return [("Draft", "New theme, not saved yet")]
    live = theme.live_revision
    if live is None:
        draft = "Not published yet: visitors don't see it"
    elif theme.has_unpublished_changes:
        draft = "Has changes visitors don't see yet"
    else:
        draft = "Matches the published version"
    site = get_active_theme()
    if site is None:
        using = "No: no theme is active yet"
    elif site.pk == theme.pk:
        using = "Yes"
    else:
        using = f"No: the site uses “{site}”"
    return [
        ("Draft", draft),
        ("Published", f"revision {live.number}" if live else "never"),
        ("Site's theme", using),
    ]


def run_publish(request, theme, activate_too):
    """Publish (and activate), telling the user what happened in messages."""
    user = request.user
    note = request.POST.get(NOTE, "").strip()[:NOTE_MAX]
    try:
        if activate_too:
            revision = publish_and_activate(theme, user=user, note=note)
        else:
            revision = publish(theme, user=user, note=note)
    except NothingToPublish:
        messages.warning(request, NOTHING_TO_PUBLISH)
    except NotPublished as error:
        messages.error(request, str(error))
    except ValidationError as error:
        messages.error(request, "Can't publish: " + " ".join(error.messages))
    except IntegrityError:
        messages.warning(request, SIMULTANEOUS)
    else:
        if revision is None:
            text = f"Nothing new to publish; “{theme}” is now the site's theme."
        elif activate_too:
            text = f"Published “{theme}” as revision {revision.number}; it's now the site's theme."
        else:
            text = f"Published “{theme}” as revision {revision.number}."
        messages.success(request, text)


class SavePublishMixin:
    """The theme admin's save, publish and activate buttons."""

    def get_urls(self):
        view = self.admin_site.admin_view
        return [
            path(
                "<path:object_id>/publish-now/",
                view(require_POST(self.row_publish_view)),
                name="capy_theme_theme_publish_now",
            ),
            path(
                "<path:object_id>/publish-and-activate/",
                view(require_POST(self.row_publish_activate_view)),
                name="capy_theme_theme_publish_activate",
            ),
            path(
                "<path:object_id>/activate/",
                view(require_POST(self.row_activate_view)),
                name="capy_theme_theme_activate",
            ),
            *super().get_urls(),
        ]

    # The theme page

    def response_add(self, request, obj, post_url_continue=None):
        return self._after_save(request, obj) or super().response_add(
            request, obj, post_url_continue
        )

    def response_change(self, request, obj):
        return self._after_save(request, obj) or super().response_change(request, obj)

    def _after_save(self, request, theme):
        """After a save from one of the three buttons: publish and activate if asked,
        and stay on the theme page. None for anything else (Django's own buttons)."""
        asked = [name for name in (SAVE, PUBLISH, PUBLISH_ACTIVATE) if name in request.POST]
        if not asked:
            return None
        if asked[0] == SAVE:
            messages.success(
                request, f"Draft of “{theme}” saved. Visitors won't see it until it's published."
            )
        elif not self.has_publish_permission(request, theme):
            messages.error(request, "The draft was saved, but you can't publish themes.")
        else:
            run_publish(request, theme, activate_too=asked[0] == PUBLISH_ACTIVATE)
        return redirect(reverse("admin:capy_theme_theme_change", args=[theme.pk]))

    def save_publish_context(self, request, theme):
        return {
            "capy_status": publish_status(theme),
            "capy_is_site_theme": theme is not None and theme.pk == site_theme_id(),
            "capy_note_max": NOTE_MAX,
        }

    # The theme list: buttons on each row

    def get_list_display(self, request):
        columns = list(super().get_list_display(request))
        if self.has_publish_permission(request):
            columns.append("publish_buttons")
        return columns

    @admin.display(description="Publish")
    def publish_buttons(self, theme):
        site_id = site_theme_id()
        buttons = []
        if theme.has_unpublished_changes:
            buttons.append(("capy_theme_theme_publish_now", "Publish"))
            if theme.pk != site_id:
                buttons.append(("capy_theme_theme_publish_activate", "Publish and activate"))
        if theme.live_revision_id is not None and theme.pk != site_id:
            buttons.append(("capy_theme_theme_activate", "Activate"))
        if not buttons:
            return "—"
        # Buttons of the list's own form (it has the CSRF token), sent to this row's view.
        return format_html_join(
            " ",
            '<button type="submit" class="button" form="changelist-form" formmethod="post" '
            'formaction="{}" aria-label="{} {}">{}</button>',
            (
                (reverse(f"admin:{name}", args=[theme.pk]), text, theme, text)
                for name, text in buttons
            ),
        )

    def _row_theme(self, request, object_id):
        theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=object_id)
        if not self.has_publish_permission(request, theme):
            raise PermissionDenied
        return theme

    def _back_to_list(self):
        return redirect(reverse("admin:capy_theme_theme_changelist"))

    def row_publish_view(self, request, object_id):
        run_publish(request, self._row_theme(request, object_id), activate_too=False)
        return self._back_to_list()

    def row_publish_activate_view(self, request, object_id):
        run_publish(request, self._row_theme(request, object_id), activate_too=True)
        return self._back_to_list()

    def row_activate_view(self, request, object_id):
        theme = self._row_theme(request, object_id)
        try:
            activate(theme)
        except NotPublished as error:
            messages.error(request, str(error))
        else:
            messages.success(request, f"“{theme}” is now the site's theme.")
        return self._back_to_list()
