from django.apps import AppConfig


class CapyThemeConfig(AppConfig):
    name = "capy_theme"
    label = "capy_theme"
    verbose_name = "Capy Theme"
    # Set here, not left to the project, so the module's migrations are the
    # same in every project whatever its DEFAULT_AUTO_FIELD.
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        from .themes import signals  # noqa: F401 (connects the cache-clearing signals)
