"""The live editor's Components view: every daisyUI component and the theme's
images in the draft theme, shown in an iframe beside the panel.

The page gets the editor's unsaved values (?changes=<JSON>, the same data the
preview endpoint takes), so image choices show before they're saved. Nothing is
written. Staff who can edit themes only; only the same site may frame it.
"""

import json

from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_GET

from ..css.custom import can_edit_custom_css, custom_css_url
from ..images.icons import square_preview
from ..models import Theme
from ..themes.active import get_site_theme, site_of
from .access import can_edit
from .custom_css_view import selectors
from .images_panel import images as images_panel
from .preview import apply_changes

# The samples, in order (templates/capy_theme/editor/components/).
COMPONENTS = [
    "text",
    "buttons",
    "badges",
    "alerts",
    "cards",
    "tabs",
    "table",
    "forms",
    "progress",
    "modal",
    "images",
]


@require_GET
@xframe_options_sameorigin
def editor_components(request, pk):
    if not can_edit(request.user):
        return HttpResponseForbidden("You can't edit themes.")
    theme = get_object_or_404(Theme.objects.select_related("live_revision"), pk=pk)
    try:
        changes = json.loads(request.GET.get("changes") or "{}")
        draft = apply_changes(theme, changes) if isinstance(changes, dict) else theme
    except ValueError, ValidationError:
        draft = theme  # half-typed values: show the saved draft
    site_theme = get_site_theme(request)
    custom = draft.settings.get("custom_css", {})
    context = {
        "theme": theme,
        "modes": ["light", "dark"],
        "sections": COMPONENTS,
        "images_panel": images_panel(draft),
        "site_name": draft.settings.get("site_name", ""),
        "domain": site_of(request),
        "site_theme": site_theme,
        "editing_site_theme": site_theme is not None and site_theme.pk == theme.pk,
        "can_edit_custom_css": can_edit_custom_css(request.user),
        "custom_selectors": selectors(custom.get("css", "")) if custom.get("enabled", True) else [],
        "published_custom_css": custom_css_url(theme.live_revision)
        if theme.live_revision
        else None,
    }
    return render(request, "capy_theme/editor/components.html", context)


@require_GET
def editor_icon_preview(request, pk):
    """A 192 px preview of the icon with the editor's unsaved background and padding.

    Made on the fly from the uploaded icon image (nothing stored): the real icon
    files are made when publishing.
    """
    if not can_edit(request.user):
        return HttpResponseForbidden("You can't edit themes.")
    theme = get_object_or_404(Theme, pk=pk)
    asset = theme.assets.filter(pk=request.GET.get("asset") or 0, slot="icon").first()
    if asset is None:
        return HttpResponseBadRequest("No such icon image.")
    background = request.GET.get("background", "")
    try:
        padding = float(request.GET.get("padding") or 0)
    except ValueError:
        padding = 0
    png = square_preview(asset, 192, max(0, min(padding, 25)) / 100, background)
    response = HttpResponse(png, content_type="image/png")
    response["Cache-Control"] = "no-store"
    return response
