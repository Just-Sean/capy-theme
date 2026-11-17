"""Saving, publishing and activating a theme from one place (#273).

The theme page has Save draft, Save and publish, and Save, publish and activate
(with a status line and a note for the history); the theme list has Publish,
Publish and activate, and Activate buttons on each row. Publishing and activating
need the publish_theme permission. Activating makes a theme the default theme: the
one every site uses unless a schedule is running or a domain has its own site
theme (themes.active.activate).
"""

from urllib.parse import urlsplit

from django.contrib import admin, messages
from django.contrib.admin.options import IS_POPUP_VAR
from django.contrib.admin.templatetags.admin_urls import add_preserved_filters
from django.contrib.admin.utils import quote, unquote
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.db.models import Exists, OuterRef
from django.http import Http404
from django.shortcuts import redirect
from django.urls import path, reverse
from django.utils.html import format_html_join
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..models import ThemeAssignment
from ..themes.active import (
    NotPublished,
    activate,
    default_theme,
    get_active_theme,
    not_published_message,
)
from ..themes.publishing import (
    NOTE_MAX,
    NOTHING_TO_PUBLISH,
    NothingToPublish,
    publish,
    publish_and_activate,
)

# The theme page's buttons (names of the submit buttons) and the note box.
SAVE = "_capy_save"
PUBLISH = "_capy_publish"
PUBLISH_ACTIVATE = "_capy_publish_activate"
NOTE = "_capy_note"

SIMULTANEOUS = (
    "Someone else just published this theme at the same moment, so yours wasn't "
    "published. Check its revisions, then publish again if needed."
)


def publish_status(theme):
    """[(label, text)] for the theme page's status line."""
    if theme is None or theme.pk is None:
        return [("Draft", "New theme, not saved yet")]
    live = theme.live_revision
    if live is None:
        draft = "Not published yet, so visitors don't see it"
    elif theme.has_unpublished_changes:
        draft = "Has changes visitors don't see yet"
    else:
        draft = "Matches the published version"
    default = default_theme()
    if default is None:
        default_text = "No (there's no default theme yet)"
    elif default.pk == theme.pk:
        default_text = "Yes"
    else:
        default_text = f"No (the default is “{default}”)"
    status = [
        ("Draft", draft),
        ("Published", f"revision {live.number}" if live else "never"),
        ("Default theme", default_text),
    ]
    showing = get_active_theme()
    if showing is not None and (default is None or showing.pk != default.pk):
        status.append(("Showing now", f"“{showing}”, because a theme schedule is running"))
    return status


def activated_message(theme):
    """What activating did: the default theme, and whether a schedule hides it."""
    showing = get_active_theme()
    if showing is not None and showing.pk != theme.pk:
        return messages.WARNING, (
            f"“{theme}” is now the default theme, but a theme schedule is showing "
            f"“{showing}” right now."
        )
    return messages.SUCCESS, f"“{theme}” is now the default theme."


def run_publish(request, theme, activate_too, quiet=False):
    """Publish (and activate), telling the user what happened in messages. When
    `quiet` (a popup, which closes straight away), success isn't said, as Django says
    nothing for a popup either; a refusal still is, so it shows on the next page."""

    def say(level, text):
        if not (quiet and level == messages.SUCCESS):
            messages.add_message(request, level, text)

    user = request.user
    note = request.POST.get(NOTE, "").strip()[:NOTE_MAX]
    try:
        if activate_too:
            revision = publish_and_activate(theme, user=user, note=note)
        else:
            revision = publish(theme, user=user, note=note)
    except NothingToPublish:
        say(messages.WARNING, NOTHING_TO_PUBLISH)
    except NotPublished:
        say(messages.ERROR, not_published_message(theme))
    except ValidationError as error:
        say(messages.ERROR, "Can't publish: " + " ".join(error.messages))
    except IntegrityError:
        say(messages.WARNING, SIMULTANEOUS)
    else:
        done = (
            f"Published “{theme}” as revision {revision.number}."
            if revision
            else "Nothing new to publish."
        )
        if not activate_too:
            say(messages.SUCCESS, done)
            return
        level, activated = activated_message(theme)
        say(level, f"{done} {activated}")


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
        and stay on the theme page (keeping the list's filters, as Django's own "Save
        and continue editing" does). In a popup, or for someone who can't open the
        theme page, Django answers as usual instead (a popup closes and fills in the
        field it was opened from), and only Django's message is shown.

        Note: Django treats a POST without its own button names as a change-form
        action if the page has an action form. ThemeAdmin has no change-form actions;
        adding one would need these buttons handled there too.
        """
        asked = [name for name in (SAVE, PUBLISH, PUBLISH_ACTIVATE) if name in request.POST]
        if not asked:
            return None
        django_answers = IS_POPUP_VAR in request.POST or not self.has_view_or_change_permission(
            request, theme
        )
        if asked[0] == SAVE:
            if not django_answers:
                text = f"Draft of “{theme}” saved. Visitors won't see it until it's published."
                if request.POST.get(NOTE, "").strip():
                    text += " The note wasn't kept: notes are only kept when you publish."
                messages.success(request, text)
        elif not self.has_publish_permission(request, theme):
            messages.error(request, "The draft was saved, but you can't publish themes.")
        else:
            run_publish(
                request,
                theme,
                activate_too=asked[0] == PUBLISH_ACTIVATE,
                quiet=IS_POPUP_VAR in request.POST,
            )
        if django_answers:
            return None
        url = reverse("admin:capy_theme_theme_change", args=[quote(theme.pk)])
        filters = {"preserved_filters": self.get_preserved_filters(request), "opts": self.opts}
        return redirect(add_preserved_filters(filters, url))

    def save_publish_context(self, request, theme):
        if theme is not None and request.method == "POST":
            # Shown again after a failed save: Django has put the unsaved values on
            # `theme`, so describe the draft as saved.
            # (If it was deleted meanwhile, describe the object Django still has.)
            theme = (
                type(theme).objects.select_related("live_revision").filter(pk=theme.pk).first()
                or theme
            )
        default = default_theme()
        return {
            "capy_status": publish_status(theme),
            "capy_is_default": theme is not None and default is not None and default.pk == theme.pk,
            "capy_note_max": NOTE_MAX,
            # What was typed, kept if the page comes back with errors.
            "capy_note": request.POST.get(NOTE, "") if request.method == "POST" else "",
            "can_publish": self.has_publish_permission(request),
        }

    # The theme list: buttons on each row

    def get_queryset(self, request):
        # Whether each theme is the default theme, in the list's own query (not one
        # query per row).
        return (
            super()
            .get_queryset(request)
            .annotate(
                capy_is_default=Exists(
                    ThemeAssignment.objects.filter(
                        theme=OuterRef("pk"), site="", starts_at=None, ends_at=None
                    )
                )
            )
        )

    def get_list_display(self, request):
        columns = list(super().get_list_display(request))
        if self.has_publish_permission(request):
            columns.append("publish_buttons")
        return columns

    @admin.display(description="Publish or activate")
    def publish_buttons(self, theme):
        is_default = theme.capy_is_default
        buttons = []
        if theme.has_unpublished_changes:
            buttons.append(
                (
                    "capy_theme_theme_publish_now",
                    "Publish",
                    "Publish “{}”? Visitors will see it wherever it's used.",
                )
            )
            if not is_default:
                buttons.append(
                    (
                        "capy_theme_theme_publish_activate",
                        "Publish and activate",
                        "Publish “{}” and make it the default theme? Visitors will see it "
                        "(unless a theme schedule is running).",
                    )
                )
        if theme.live_revision_id is not None and not is_default:
            buttons.append(
                (
                    "capy_theme_theme_activate",
                    "Activate",
                    "Make the published version of “{}” the default theme? Visitors will "
                    "see it (unless a theme schedule is running).",
                )
            )
        if not buttons:
            return "—"
        # Buttons of the list's own form (it has the CSRF token), sent to this row's
        # view. admin/confirm.js asks first; without JavaScript they just go.
        return format_html_join(
            " ",
            '<button type="submit" class="button capy-row-button" form="changelist-form" '
            'formmethod="post" formaction="{}" aria-label="{} {}" data-capy-confirm="{}">'
            "{}</button>",
            (
                (reverse(f"admin:{name}", args=[theme.pk]), text, theme, ask.format(theme), text)
                for name, text, ask in buttons
            ),
        )

    def _row_theme(self, request, object_id):
        # get_object returns None for an id that's missing or malformed (e.g. "abc").
        theme = self.get_object(request, unquote(object_id))
        if theme is None:
            raise Http404("No such theme.")
        if not self.has_publish_permission(request, theme):
            raise PermissionDenied
        return theme

    def _back_to_list(self, request):
        """Back to the list as it was (its filters, search and page), if the request
        came from it; otherwise to the plain list."""
        changelist = reverse("admin:capy_theme_theme_changelist")
        if not self.has_view_or_change_permission(request):
            return redirect(reverse("admin:index"))  # they can't open the list
        came_from = request.META.get("HTTP_REFERER", "")
        safe = url_has_allowed_host_and_scheme(
            came_from, allowed_hosts={request.get_host()}, require_https=request.is_secure()
        )
        if safe and urlsplit(came_from).path == changelist:
            return redirect(came_from)
        return redirect(changelist)

    def row_publish_view(self, request, object_id):
        run_publish(request, self._row_theme(request, object_id), activate_too=False)
        return self._back_to_list(request)

    def row_publish_activate_view(self, request, object_id):
        run_publish(request, self._row_theme(request, object_id), activate_too=True)
        return self._back_to_list(request)

    def row_activate_view(self, request, object_id):
        theme = self._row_theme(request, object_id)
        try:
            activate(theme)
        except NotPublished:
            messages.error(request, not_published_message(theme))
        else:
            level, text = activated_message(theme)
            messages.add_message(request, level, text)
        return self._back_to_list(request)
