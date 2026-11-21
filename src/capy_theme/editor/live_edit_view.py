"""The live edit page (issue #229): capy-theme's own page for building a theme.

It shows the header (logo, site name, tagline, Light / Dark / Auto, a menu to switch
the theme being edited)
and every daisyUI component, with the live editor open on it. It's part of the
module, with its own template and bundled daisyUI stylesheet, so it looks and works
the same in every project, whatever the project's own pages, base template or
Tailwind build. Staff who can edit themes only. It needs Django's admin at its
usual `admin` namespace (as the rest of capy-theme does), for the login and links.
"""

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.clickjacking import xframe_options_deny
from django.views.decorators.http import require_GET

from .. import conf
from ..css.stylesheet import stylesheet_url
from ..fonts.library import external_stylesheets
from ..images.logo_tag import logo_html
from ..models import Theme
from ..themes.active import get_active_theme
from .access import can_edit, requested_theme_id
from .state import editor_urls


def draft_header(theme):
    """The header for the theme being edited, from its draft (#271): logo, site
    name and tagline. The logo carries the editor's marker, so it previews too."""
    settings = theme.settings
    site_name = settings.get("site_name", "")
    marker = {"data-capy-logo-slot": "logo_main", "data-capy-logo-attrs": "{}"}
    return {
        "logo": logo_html(
            theme.snapshot(), "logo_main", settings.get("logo_alt") or site_name, {}, marker
        ),
        "site_name": site_name,
        "tagline": settings.get("tagline", ""),
    }


def theme_to_edit(request):
    """The active theme, or else the first theme, or None if there are none."""
    active = get_active_theme(request)
    if active is not None:
        return active
    return Theme.objects.order_by("pk").first()


@require_GET
@never_cache
@xframe_options_deny  # the editor's Save and Publish must never be clicked from a frame
def live_edit(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), login_url=reverse("admin:login"))
    if not can_edit(request.user):
        raise PermissionDenied("You can't edit themes.")  # the project's 403 page
    # The editor opens on the theme named in ?edit=; without one, on the active theme.
    requested = requested_theme_id(request)
    if requested is None:
        theme = theme_to_edit(request)
        if theme is not None:
            return redirect(f"{reverse('capy_theme:live_edit')}?edit={theme.pk}")
    editing = Theme.objects.filter(pk=requested).first() if requested is not None else None
    # The page is self-contained: it links the theme's stylesheet and mounts the editor
    # itself, so it needs neither the project's context processors nor capy-theme's public
    # tags (the editor is capy-theme's own tool, previewing on its own page).
    context = {
        "request": request,
        "editing": editing,
        "no_theme": not Theme.objects.exists(),
        "missing_theme": requested is not None and editing is None,
        "header": draft_header(editing) if editing else None,
        "stylesheet_url": _stylesheet_url(editing),
        "font_stylesheets": _font_stylesheets(editing),
        "editor": _editor_mount(editing) if editing else None,
        # Every theme, for the menu that switches the theme being edited (#269).
        "edit_choices": Theme.objects.only("pk", "name", "live_revision"),
    }
    return render(request, "capy_theme/editor/live_edit.html", context)


def _stylesheet_url(editing):
    """The editing theme's published stylesheet, or "" (the editor injects the draft CSS)."""
    if editing is None or editing.live_revision_id is None:
        return ""
    return stylesheet_url(editing.live_revision)


def _font_stylesheets(editing):
    """External font stylesheets (e.g. Google Fonts) the editing theme's draft needs."""
    if editing is None:
        return []
    return external_stylesheets(editing.snapshot().get("fonts"))


def _editor_mount(editing):
    """The context the editor mount (mount.html) needs for the theme being edited."""
    return {
        "theme": editing,
        "urls": editor_urls(editing),
        "floating_button": conf.get("CAPY_THEME_EDITOR_BUTTON"),
    }
