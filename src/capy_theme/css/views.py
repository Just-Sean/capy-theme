"""Serving a revision's theme stylesheet and its custom CSS."""

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from ..models import ThemeRevision
from .custom import custom_css
from .stylesheet import render_css

ONE_YEAR = 60 * 60 * 24 * 365


def theme_css(request, version):
    """Serve a revision's stylesheet. Every URL names one revision, so it never changes."""
    revision = get_object_or_404(ThemeRevision.objects.select_related("theme"), css_version=version)
    response = HttpResponse(render_css(revision), content_type="text/css; charset=utf-8")
    response["Cache-Control"] = f"public, max-age={ONE_YEAR}, immutable"
    return response


def custom_css_file(request, version):
    """Serve a revision's custom CSS (404 if it has none or it's switched off)."""
    revision = get_object_or_404(ThemeRevision, css_version=version)
    css = custom_css(revision.snapshot)
    if not css:
        raise Http404("This revision has no custom CSS.")
    response = HttpResponse(css + "\n", content_type="text/css; charset=utf-8")
    response["Cache-Control"] = f"public, max-age={ONE_YEAR}, immutable"
    return response
