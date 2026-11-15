"""The live edit page (issue #229): capy-theme's own page for building a theme.

It shows the header (logo, site name, tagline, Light / Dark / Auto, theme picker)
and every daisyUI component, with the live editor open on it. It's part of the
module, with its own template and bundled daisyUI stylesheet, so it looks and works
the same in every project, whatever the project's own pages, base template or
Tailwind build. Staff who can edit themes only.
"""

from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from ..context_processors import theme as theme_context
from ..models import Theme
from ..themes.active import get_active_theme
from .access import can_edit


def theme_to_edit(request):
    """The active theme, or else the first theme, or None if there are none."""
    active = get_active_theme(request)
    if active is not None:
        return active
    return Theme.objects.order_by("pk").first()


@require_GET
@never_cache
def live_edit(request):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), login_url=reverse("admin:login"))
    if not can_edit(request.user):
        return HttpResponseForbidden("You can't edit themes.")
    # The editor opens on the theme named in ?edit=; without one, on the active theme.
    if not request.GET.get("edit", "").isdigit():
        theme = theme_to_edit(request)
        if theme is not None:
            return redirect(f"{reverse('capy_theme:live_edit')}?edit={theme.pk}")
    # `theme` and `request` are given here, so the page doesn't depend on the
    # project's context processors.
    context = {
        **theme_context(request),
        "request": request,
        "no_theme": not Theme.objects.exists(),
    }
    return render(request, "capy_theme/editor/live_edit.html", context)
