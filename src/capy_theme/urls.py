"""The module's URLs.

A project includes them under /theme/ in its urls.py, with
`path("theme/", include("capy_theme.urls"))`.
"""

from django.urls import path

from .artifacts import downloads
from .artifacts.api import api_view
from .css import views as css_views
from .editor import components_view, custom_css_view
from .editor import views as editor_views
from .themes import views as theme_views

app_name = "capy_theme"

urlpatterns = [
    path("mode/<slug:mode>/", theme_views.set_mode, name="set_mode"),
    path("choose/<slug:slug>/", theme_views.choose_theme, name="choose_theme"),
    path(
        "editor/<int:pk>/components/", components_view.editor_components, name="editor_components"
    ),
    path(
        "editor/<int:pk>/icon-preview.png",
        components_view.editor_icon_preview,
        name="editor_icon_preview",
    ),
    path("editor/<int:pk>/custom.css", custom_css_view.editor_custom_css, name="editor_custom_css"),
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
    path("tokens.json", downloads.design_tokens, name="design_tokens"),
    path("daisyui-theme.css", downloads.daisyui_theme, name="daisyui_theme"),
    path("custom/<slug:version>.css", css_views.custom_css_file, name="custom_css"),
    path("<slug:version>.css", css_views.theme_css, name="theme_css"),
]
