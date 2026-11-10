"""Adding the live editor to a page (through {% theme_head %})."""

from django.conf import settings as django_settings
from django.template.loader import render_to_string

from .access import can_edit, editor_theme
from .state import editor_urls


def mount(request):
    """The editor's <head> tags for this request, or "" if this user can't edit.

    Output by {% theme_head %}, so the editor works on every page that uses it.
    """
    user = getattr(request, "user", None)  # absent without Django's auth middleware
    if user is None or not can_edit(user):
        return ""
    theme = editor_theme(request)
    if theme is None:
        return ""
    context = {
        "editor": {
            "theme": theme,
            "urls": editor_urls(theme),
            "floating_button": getattr(django_settings, "CAPY_THEME_EDITOR_BUTTON", True),
        }
    }
    return render_to_string("capy_theme/editor/mount.html", context, request=request)
