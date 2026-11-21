"""Who can use the live editor, and which theme it edits."""


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


def requested_theme_id(request):
    """The theme id in ?edit=<id>, or None if there isn't a valid one.

    Only ASCII digits count: str.isdigit() also accepts characters like "²", which
    int() can't read, so a crafted URL would crash the page."""
    requested = request.GET.get("edit", "")
    if requested.isascii() and requested.isdigit():
        return int(requested)
    return None
