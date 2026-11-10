from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from .models import ThemeRevision
from .stylesheet import render_css

ONE_YEAR = 60 * 60 * 24 * 365


def theme_css(request, version):
    """Serve a revision's stylesheet. Every URL names one revision, so it never changes."""
    revision = get_object_or_404(ThemeRevision.objects.select_related("theme"), css_version=version)
    response = HttpResponse(render_css(revision), content_type="text/css; charset=utf-8")
    response["Cache-Control"] = f"public, max-age={ONE_YEAR}, immutable"
    return response
