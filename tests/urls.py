"""URLs for the test project: the admin, the module's URLs under /theme/, and one
ordinary page (/page/) that links the theme's stylesheet from the exposed data, the way
a v2 consumer does (capy-theme injects nothing into the page itself)."""

from django.contrib import admin
from django.http import HttpResponse
from django.template import engines
from django.urls import include, path

PAGE = engines["django"].from_string(
    "{% load capy_theme %}{% theme_artifacts as t %}"
    "<!doctype html><html><head>"
    '{% if t %}<link rel="stylesheet" href="{{ t.stylesheet_url }}">{% endif %}'
    "</head><body><h1>A project page</h1></body></html>"
)


def page(request):
    return HttpResponse(PAGE.render({}, request))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("theme/", include("capy_theme.urls")),
    path("page/", page),
]
