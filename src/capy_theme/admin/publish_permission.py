"""Admin pages that change which theme is live need the publish_theme permission."""


class PublishPermissionMixin:
    """Viewing needs view_theme (or publish_theme); changing needs publish_theme."""

    def _can_publish(self, request):
        return request.user.has_perm("capy_theme.publish_theme")

    def has_add_permission(self, request):
        return self._can_publish(request)

    def has_change_permission(self, request, obj=None):
        return self._can_publish(request)

    def has_delete_permission(self, request, obj=None):
        return self._can_publish(request)

    def has_view_permission(self, request, obj=None):
        return request.user.has_perm("capy_theme.view_theme") or self._can_publish(request)

    def has_module_permission(self, request):
        return self.has_view_permission(request)
