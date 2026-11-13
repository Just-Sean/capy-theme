# src/capy_theme/admin/publish_permission.py

**What it is:** `PublishPermissionMixin`, used by the schedule and site-theme admins. These pages change which theme is live, so adding, changing or deleting requires `publish_theme`. Viewing needs `view_theme` or `publish_theme`.
