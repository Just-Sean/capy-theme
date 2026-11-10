"""Clear the active-theme cache whenever themes, revisions or assignments change."""

from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from ..models import Theme, ThemeAssignment, ThemeRevision
from .active import clear_cache


@receiver([post_save, post_delete], sender=Theme)
@receiver([post_save, post_delete], sender=ThemeRevision)
@receiver([post_save, post_delete], sender=ThemeAssignment)
def theme_data_changed(**kwargs):
    clear_cache()
