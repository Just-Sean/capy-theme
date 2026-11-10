"""Database models for this module. Each section keeps its own models; Django finds
them through this file.

To link to users, use settings.AUTH_USER_MODEL (never import a project's User):

    from django.conf import settings
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
"""

from .fonts.models import Font, FontFile
from .images.models import ThemeAsset, ThemeAssetVariant
from .themes.models.assignment import ScheduledTheme, SiteTheme, ThemeAssignment
from .themes.models.revision import ThemeRevision
from .themes.models.theme import Theme

__all__ = [
    "Font",
    "FontFile",
    "ScheduledTheme",
    "SiteTheme",
    "Theme",
    "ThemeAsset",
    "ThemeAssetVariant",
    "ThemeAssignment",
    "ThemeRevision",
]
