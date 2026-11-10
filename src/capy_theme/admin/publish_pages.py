"""The theme admin's own pages: Publish, Revisions (with compare) and Restore."""

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from ..models import Theme
from ..themes.history import compare as compare_revisions
from ..themes.history import restore as restore_revision
from ..themes.publishing import NothingToPublish, publish
from .fonts import _int


class PublishForm(forms.Form):
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3, "cols": 60}),
        help_text="Optional: what changed or why, for the history.",
    )


class PublishPagesMixin:
    """Adds the Publish, Revisions and Restore pages to ThemeAdmin."""

    def get_urls(self):
        return [
            path(
                "<path:object_id>/publish/",
                self.admin_site.admin_view(self.publish_view),
                name="capy_theme_theme_publish",
            ),
            path(
                "<path:object_id>/revisions/",
                self.admin_site.admin_view(self.revisions_view),
                name="capy_theme_theme_revisions",
            ),
            path(
                "<path:object_id>/revisions/<int:number>/restore/",
                self.admin_site.admin_view(self.restore_view),
                name="capy_theme_theme_restore",
            ),
            *super().get_urls(),
        ]

    def publish_view(self, request, object_id):
        theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=object_id)
        if not self.has_publish_permission(request, theme):
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

    # Revisions: list, compare and restore

    def revisions_view(self, request, object_id):
        theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=object_id)
        if not self.has_view_or_change_permission(request, theme):
            raise PermissionDenied
        revisions = list(theme.revisions.select_related("published_by"))
        numbers = [r.number for r in revisions]
        older = _int(request.GET.get("a"), numbers[1] if len(numbers) > 1 else None)
        newer = _int(request.GET.get("b"), numbers[0] if numbers else None)
        by_number = {r.number: r for r in revisions}
        differences = None
        if older in by_number and newer in by_number:
            differences = compare_revisions(by_number[older], by_number[newer])
        context = {
            **self.admin_site.each_context(request),
            "title": f"Revisions of “{theme}”",
            "opts": self.opts,
            "theme": theme,
            "revisions": revisions,
            "older": older,
            "newer": newer,
            "differences": differences,
            "can_restore": self.has_publish_permission(request, theme),
            "change_url": reverse("admin:capy_theme_theme_change", args=[theme.pk]),
        }
        return TemplateResponse(request, "capy_theme/admin/revisions.html", context)

    def restore_view(self, request, object_id, number):
        theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=object_id)
        if not self.has_publish_permission(request, theme):
            raise PermissionDenied
        revision = get_object_or_404(theme.revisions, number=number)
        revisions_url = reverse("admin:capy_theme_theme_revisions", args=[theme.pk])
        if request.method == "POST":
            try:
                new = restore_revision(theme, revision, user=request.user)
            except NothingToPublish:
                messages.warning(request, f"Revision {number} is already what's live.")
            except ValidationError as error:
                messages.error(request, "Can't restore: " + " ".join(error.messages))
            except IntegrityError:
                messages.warning(
                    request, "Someone else just published this theme. Check, then try again."
                )
            else:
                messages.success(
                    request, f"Restored revision {number}. It's live as revision {new.number}."
                )
            return redirect(revisions_url)
        context = {
            **self.admin_site.each_context(request),
            "title": f"Restore revision {number} of “{theme}”",
            "opts": self.opts,
            "theme": theme,
            "revision": revision,
            "differences": compare_revisions(theme.live_revision, revision)
            if theme.live_revision
            else None,
            "revisions_url": revisions_url,
        }
        return TemplateResponse(request, "capy_theme/admin/restore.html", context)
