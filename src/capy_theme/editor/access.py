"""Who can use the live editor, which theme it edits, and adding it to pages."""

from ..models import Theme
from ..themes.active import get_active_theme


def can_edit(user):
    """Staff who can change themes can open the editor."""
    return bool(
        user.is_authenticated
        and user.is_active
        and user.is_staff
        and user.has_perm("capy_theme.change_theme")
    )


def can_publish(user):
    return can_edit(user) and user.has_perm("capy_theme.publish_theme")


def editor_theme(request):
    """The theme the editor works on: ?edit=<id> if given, else the active theme."""
    requested = request.GET.get("edit", "")
    if requested.isdigit():
        return Theme.objects.filter(pk=int(requested)).first()
    active = get_active_theme(request)
    return Theme.objects.filter(pk=active.pk).first() if active else None
