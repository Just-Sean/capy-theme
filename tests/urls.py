"""URLs for the test project: the admin, the module's URLs under /theme/, and one
ordinary page (/page/) that includes {% theme_head %}, like any project page."""

from django.contrib import admin
from django.http import HttpResponse
from django.template import engines
from django.urls import include, path

PAGE = engines["django"].from_string(
    "{% load capy_theme %}<!doctype html><html {% theme_html_attrs %}><head>"
    "{% theme_head %}</head><body><h1>A project page</h1></body></html>"
)


def page(request):
    return HttpResponse(PAGE.render({}, request))


urlpatterns = [
    path("admin/", admin.site.urls),
    path("theme/", include("capy_theme.urls")),
    path("page/", page),
]
