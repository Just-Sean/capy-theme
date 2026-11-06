"""Database models for this module.

To link to users, use settings.AUTH_USER_MODEL (never import a project's User):

    from django.conf import settings
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
"""

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from .validation import validate_base, validate_settings


class Theme(models.Model):
    """A saved theme: two built-in daisyUI bases plus the overrides in `settings`.

    `settings` is the draft. Every value a theme changes lives there, checked
    against settings.schema.json. It starts empty.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    # Names of built-in daisyUI themes (see catalogue.py). Not stored as model
    # `choices`, because the list depends on the CAPY_THEME_BUILTIN_THEMES setting
    # and choices would end up in migrations. Checked in clean() instead.
    light_base = models.CharField(
        max_length=50, default="light", help_text="The built-in daisyUI theme used in light mode."
    )
    dark_base = models.CharField(
        max_length=50, default="dark", help_text="The built-in daisyUI theme used in dark mode."
    )
    settings = models.JSONField(
        default=dict,
        blank=True,
        validators=[validate_settings],
        help_text="Every override on top of the base themes.",
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Checked on every save, not only in forms, so bad data can't be saved
        # from code either.
        validate_settings(self.settings)
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
            try:
                validate_base(getattr(self, field), scheme)
            except ValidationError as error:
                errors[field] = error.messages
        if errors:
            raise ValidationError(errors)
