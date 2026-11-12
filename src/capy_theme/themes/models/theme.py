"""The Theme model: a theme's draft look (bases and settings)."""

import copy
import uuid

from django.core.exceptions import ValidationError
from django.db import models

from ...fonts.library import snapshot_fonts
from ...fonts.models import Font
from ...images.logos import snapshot_images
from ...images.models import ThemeAsset
from ..catalog import builtin_values
from ..validation import validate_base, validate_settings


class Theme(models.Model):
    """A saved theme: two built-in daisyUI bases plus the overrides in `settings`.

    The fields here are the draft: editing a theme changes only the draft.
    Publishing (see themes/publishing.py) copies the draft's look into a ThemeRevision,
    and `live_revision` points at the one pages use.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    # Names of built-in daisyUI themes (see themes/catalog.py). Not stored as model
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
    offered_to_visitors = models.BooleanField(
        default=False,
        help_text="Visitors can choose this theme with {% theme_picker %} (once it's published).",
    )
    live_revision = models.ForeignKey(
        "ThemeRevision",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
        help_text="The published revision pages use. Empty until the theme is first published.",
    )
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        permissions = [
            ("publish_theme", "Can publish, activate and restore themes"),
            ("edit_custom_css", "Can edit a theme's custom CSS"),
            ("import_theme", "Can import themes"),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Checked on every save, not only in forms, so bad data can't be saved
        # from code either.
        validate_settings(self.settings)
        self.clean()
        # Only publishing changes live_revision (it saves with update_fields).
        # An ordinary save of an existing theme leaves it alone, so a copy loaded
        # before someone published can't overwrite the live revision.
        if not self._state.adding and kwargs.get("update_fields") is None:
            kwargs["update_fields"] = [
                field.name
                for field in self._meta.concrete_fields
                if not field.primary_key and field.name != "live_revision"
            ]
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()
        errors = {}
        missing = set(self.settings.get("fonts", {}).values()) - set(
            Font.objects.filter(pk__in=self.settings.get("fonts", {}).values()).values_list(
                "pk", flat=True
            )
        )
        if missing:
            errors["settings"] = [f"Font {pk} isn't in the font library." for pk in sorted(missing)]
        image_errors = self._image_errors()
        if image_errors:
            errors["settings"] = errors.get("settings", []) + image_errors
        for field, scheme in (("light_base", "light"), ("dark_base", "dark")):
            try:
                validate_base(getattr(self, field), scheme)
            except ValidationError as error:
                errors[field] = error.messages
        if errors:
            raise ValidationError(errors)

    def _image_errors(self):
        """Chosen images must be this theme's, uploaded for that slot."""
        chosen = self.settings.get("images", {})
        wanted = {(slot, pk) for slot, modes in chosen.items() for pk in modes.values()}
        if not wanted:
            return []
        found = set()
        if self.pk is not None:
            found = set(
                ThemeAsset.objects.filter(theme=self, pk__in={pk for _, pk in wanted}).values_list(
                    "slot", "pk"
                )
            )
        return [
            f"Image {pk} isn't one of this theme's {slot} images."
            for slot, pk in sorted(wanted - found)
        ]

    def snapshot(self):
        """Return the draft's look: everything a revision copies when published.

        The name and slug are admin labels, so they aren't part of it: renaming
        a theme takes effect without publishing.
        """
        snapshot = {
            "light_base": self.light_base,
            "dark_base": self.dark_base,
            # The bases' full values are copied too, so a later daisyUI update
            # can't change or break a published theme. None if the base no
            # longer exists (such a draft can't be published).
            "light_values": builtin_values(self.light_base),
            "dark_values": builtin_values(self.dark_base),
            "settings": copy.deepcopy(self.settings),
        }
        # The chosen logos and images: their files, sizes and smaller copies.
        # Images are never changed after upload, so older revisions keep theirs.
        images = snapshot_images(self, self.settings)
        if images:
            snapshot["images"] = images
        # Chosen fonts are copied in (family, fallbacks, file URLs), so later
        # changes to the font library can't change a published theme. Only
        # added when fonts are chosen, so older revisions still compare equal.
        fonts = snapshot_fonts(self.settings)
        if fonts:
            snapshot["fonts"] = fonts
        return snapshot

    def base_changes(self):
        """Return notes on daisyUI changes to the live revision's base themes.

        The live revision keeps the base values saved when it was published. If
        the daisyUI catalog the module now ships has different values for a
        base, or no longer has it, this explains that the site still uses the
        saved version. Empty if nothing changed or the theme isn't published.
        """
        live = self.live_revision
        if live is None:
            return []
        notes = []
        for scheme in ("light", "dark"):
            name = live.snapshot.get(f"{scheme}_base")
            current = builtin_values(name)
            if current is None:
                notes.append(
                    f"“{name}” no longer exists in daisyUI. Your site keeps using the saved "
                    f"version. Choose a new {scheme} base to publish changes."
                )
            elif current != live.snapshot.get(f"{scheme}_values"):
                notes.append(
                    f"daisyUI has changed “{name}” since this theme was published. Your site "
                    "keeps using the saved version. Publish again to use daisyUI's new one."
                )
        return notes

    @property
    def has_unpublished_changes(self):
        """True if the draft's look differs from the live revision (or was never published)."""
        if self.live_revision is None:
            return True
        live = dict(self.live_revision.snapshot)
        if not live.get("logo"):
            live.pop("logo", None)  # revisions from before logo slots had "logo": ""
        return self.snapshot() != live
