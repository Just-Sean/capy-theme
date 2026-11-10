"""The module's URLs.

A project includes them under /theme/ in its urls.py, with
`path("theme/", include("capy_theme.urls"))`.
"""

from django.urls import path

from . import views

app_name = "capy_theme"

urlpatterns = [
    path("showcase/", views.showcase, name="showcase"),
    path("mode/<slug:mode>/", views.set_mode, name="set_mode"),
    path("editor/<int:pk>/state/", views.editor_state, name="editor_state"),
    path("editor/<int:pk>/preview/", views.editor_preview, name="editor_preview"),
    path("editor/<int:pk>/suggestions/", views.editor_suggestions, name="editor_suggestions"),
    path("<slug:version>.css", views.theme_css, name="theme_css"),
]
