"""The theme admin's Export button and Import theme page (see portability/)."""

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse

from ..models import Theme
from ..portability.export import export_theme
from ..portability.importing import import_theme


class ImportForm(forms.Form):
    file = forms.FileField(
        label="Theme export (.zip)",
        help_text="A zip made with Export on another site's theme page.",
    )


class ImportExportMixin:
    """Adds Export (download a theme as a zip) and Import theme to ThemeAdmin."""

    def get_urls(self):
        return [
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name="capy_theme_theme_import",
            ),
            path(
                "<path:object_id>/export/",
                self.admin_site.admin_view(self.export_view),
                name="capy_theme_theme_export",
            ),
            *super().get_urls(),
        ]

    def changelist_view(self, request, extra_context=None):
        extra_context = {**(extra_context or {}), "can_import": self.has_import_permission(request)}
        return super().changelist_view(request, extra_context)

    def has_import_permission(self, request):
        return request.user.has_perm("capy_theme.import_theme")

    def export_view(self, request, object_id):
        theme = get_object_or_404(Theme, pk=object_id)
        if not self.has_view_or_change_permission(request, theme):
            raise PermissionDenied
        response = HttpResponse(export_theme(theme), content_type="application/zip")
        response["Content-Disposition"] = f'attachment; filename="{theme.slug}.capy-theme.zip"'
        return response

    def import_view(self, request):
        if not self.has_import_permission(request):
            raise PermissionDenied
        form = ImportForm(request.POST or None, request.FILES or None)
        if request.method == "POST" and form.is_valid():
            try:
                theme = import_theme(
                    form.cleaned_data["file"],
                    keep_custom_css=request.user.has_perm("capy_theme.edit_custom_css"),
                )
            except ValidationError as error:
                form.add_error("file", error)
            else:
                messages.success(
                    request,
                    f"Imported “{theme}” as a draft. Check it, then publish and activate it.",
                )
                return redirect(reverse("admin:capy_theme_theme_change", args=[theme.pk]))
        context = {
            **self.admin_site.each_context(request),
            "title": "Import a theme",
            "opts": self.opts,
            "form": form,
        }
        return TemplateResponse(request, "capy_theme/admin/import_theme.html", context)
