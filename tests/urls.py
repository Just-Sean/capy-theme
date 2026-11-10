"""URLs for the test project: the admin and the module's URLs under /theme/."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("theme/", include("capy_theme.urls")),
]
