"""URLs for the test project. Add the module's URLs here once it has some."""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
]
