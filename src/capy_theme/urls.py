"""The module's URLs.

A project includes them under /theme/ in its urls.py, with
`path("theme/", include("capy_theme.urls"))`.
"""

from django.urls import path

from .artifacts.api import api_view
from .css import views as css_views
from .editor import views as editor_views
from .themes import views as theme_views

app_name = "capy_theme"

urlpatterns = [
    path("mode/<slug:mode>/", theme_views.set_mode, name="set_mode"),
    path("choose/<slug:slug>/", theme_views.choose_theme, name="choose_theme"),
    path("editor/<int:pk>/components/", editor_views.editor_components, name="editor_components"),
    path("editor/visitor-view/", editor_views.editor_visitor_view, name="editor_visitor_view"),
    path("editor/<int:pk>/state/", editor_views.editor_state, name="editor_state"),
    path("editor/<int:pk>/preview/", editor_views.editor_preview, name="editor_preview"),
    path(
        "editor/<int:pk>/suggestions/", editor_views.editor_suggestions, name="editor_suggestions"
    ),
    path("editor/<int:pk>/save/", editor_views.editor_save, name="editor_save"),
    path("editor/<int:pk>/upload/", editor_views.editor_upload, name="editor_upload"),
    path("editor/<int:pk>/publish/", editor_views.editor_publish, name="editor_publish"),
    path("api.json", api_view(), name="api"),
    path("<slug:version>.css", css_views.theme_css, name="theme_css"),
]
