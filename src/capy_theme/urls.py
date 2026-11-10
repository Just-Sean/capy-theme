"""The module's URLs.

A project includes them under /theme/ in its urls.py, with
`path("theme/", include("capy_theme.urls"))`.
"""

from django.urls import path

from . import views

app_name = "capy_theme"

urlpatterns = [
    path("<slug:version>.css", views.theme_css, name="theme_css"),
]
