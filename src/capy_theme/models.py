"""Database models for this module.

To link to users, use settings.AUTH_USER_MODEL (never import a project's User):

    from django.conf import settings
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
"""

import copy
import uuid

from django.conf import settings as django_settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .catalogue import builtin_values
from .fonts import snapshot_fonts
from .images import MODES, SLOT_CHOICES
from .logos import snapshot_images
from .validation import validate_base, validate_settings


class Theme(models.Model):
    """A saved theme: two built-in daisyUI bases plus the overrides in `settings`.

    The fields here are the draft: editing a theme changes only the draft.
    Publishing (see publishing.py) copies the draft's look into a ThemeRevision,
    and `live_revision` points at the one pages use.
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
        the daisyUI catalogue the module now ships has different values for a
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


class ThemeRevision(models.Model):
    """A published copy of a theme's look. Never edited after it's created.

    Created only by publishing.publish(). Kept for history and, later, compare
    and restore.
    """

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="revisions")
    number = models.PositiveIntegerField(help_text="1 for the theme's first publish, then 2, 3…")
    snapshot = models.JSONField(
        help_text="The theme's light and dark base names and their values, logo and settings."
    )
    css_version = models.CharField(
        max_length=16,
        unique=True,
        editable=False,
        help_text="Short hash naming this revision's stylesheet: /theme/<css_version>.css",
    )
    note = models.TextField(blank=True, help_text="Why it was published (optional).")
    published_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    published_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["theme", "-number"]
        constraints = [
            models.UniqueConstraint(fields=["theme", "number"], name="unique_revision_number"),
        ]

    def __str__(self):
        return f"{self.theme} revision {self.number}"


class ThemeAssignment(models.Model):
    """Which theme is active on the site.

    The default assignment has no dates; change it with active.activate().
    Scheduled assignments have a start and/or end date and win while they're
    running (start ≤ now < end), e.g. a holiday theme. The site field is for
    multiple sites (8.2) and is ignored until then.
    """

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="assignments")
    site = models.CharField(
        max_length=255, blank=True, help_text="Domain this applies to. Blank means every site."
    )
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            # Only one default (undated) assignment per site.
            models.UniqueConstraint(
                fields=["site"],
                condition=models.Q(starts_at__isnull=True, ends_at__isnull=True),
                name="one_default_assignment_per_site",
            ),
        ]

    def __str__(self):
        if not self.is_scheduled:
            return f"{self.theme} (default)"
        return f"{self.theme} ({self.starts_at or '…'} to {self.ends_at or '…'})"

    @property
    def is_scheduled(self):
        return self.starts_at is not None or self.ends_at is not None

    def is_running(self, now):
        """True if `now` is inside the dates (start included, end not)."""
        return (self.starts_at is None or self.starts_at <= now) and (
            self.ends_at is None or now < self.ends_at
        )

    def clean(self):
        super().clean()
        if self.starts_at and self.ends_at and self.ends_at <= self.starts_at:
            raise ValidationError({"ends_at": "The end must be after the start."})
        if self.theme_id and self.theme.live_revision_id is None:
            raise ValidationError({"theme": "Publish this theme before scheduling it."})


class ScheduledTheme(ThemeAssignment):
    """The admin's view of scheduled assignments (those with dates)."""

    class Meta:
        proxy = True
        verbose_name = "scheduled theme"
        verbose_name_plural = "theme schedule"


class Font(models.Model):
    """A font in the library, shared by all themes. Its files are in FontFile."""

    SOURCES = [
        ("system", "System font stack"),
        ("bundled", "Bundled with capy-theme"),
        ("upload", "Uploaded"),
        ("google", "Imported from Google Fonts"),
        ("external", "External stylesheet"),
    ]

    family = models.CharField(
        max_length=100, unique=True, help_text="The font's name, e.g. Inter or Source Serif."
    )
    source = models.CharField(max_length=20, choices=SOURCES, default="upload")
    fallback_stack = models.CharField(
        max_length=300,
        blank=True,
        help_text="Fonts to use while this one loads or if it can't, e.g. "
        "ui-sans-serif, system-ui, sans-serif. Blank uses a sensible default for the role.",
    )
    licence = models.TextField(blank=True, help_text="The font's licence, or where to find it.")
    stylesheet_url = models.URLField(
        blank=True, help_text="For external fonts only: the stylesheet that loads it."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["family"]

    def __str__(self):
        return self.family

    def clean(self):
        super().clean()
        if self.source == "external":
            if not self.stylesheet_url.startswith("https://"):
                raise ValidationError(
                    {"stylesheet_url": "External fonts need their stylesheet's https:// address."}
                )
        elif self.stylesheet_url:
            raise ValidationError(
                {"stylesheet_url": "Only external fonts use a stylesheet address."}
            )


class FontFile(models.Model):
    """One WOFF2 file of a font: a weight and style, optionally for one character subset."""

    STYLES = [("normal", "Normal"), ("italic", "Italic")]

    font = models.ForeignKey(Font, on_delete=models.CASCADE, related_name="files")
    weight = models.PositiveSmallIntegerField(
        default=400, help_text="100 (thin) to 900 (black); 400 is regular, 700 bold."
    )
    style = models.CharField(max_length=10, choices=STYLES, default="normal")
    subset = models.CharField(
        max_length=50, default="latin", help_text="Which characters it covers, e.g. latin."
    )
    unicode_range = models.CharField(
        max_length=500, blank=True, help_text="Optional CSS unicode-range for this subset."
    )
    file = models.FileField(upload_to="capy_theme/fonts/", help_text="A WOFF2 font file.")

    class Meta:
        ordering = ["font", "weight", "style"]

    def __str__(self):
        return f"{self.font} {self.weight} {self.style} ({self.subset})"


def asset_path(asset, filename):
    return f"capy_theme/assets/{asset.slot}/{filename}"


class ThemeAsset(models.Model):
    """An image a theme uses: a logo, the icon, the sharing image or a background.

    Never edited after upload: a new image is a new asset, so older revisions keep
    showing theirs. Generated sizes and formats are in ThemeAssetVariant.
    """

    theme = models.ForeignKey(Theme, on_delete=models.CASCADE, related_name="assets")
    slot = models.CharField(max_length=40, choices=SLOT_CHOICES)
    mode = models.CharField(max_length=10, choices=MODES, default="light")
    original = models.FileField(upload_to=asset_path)
    alt_text = models.CharField(max_length=200, blank=True)
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    size = models.PositiveIntegerField(default=0, help_text="File size in bytes.")
    content_type = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["theme", "slot", "mode", "-created_at"]

    def __str__(self):
        return f"{self.theme} {self.slot} ({self.mode})"


def variant_path(variant, filename):
    return f"capy_theme/assets/{variant.asset.slot}/variants/{filename}"


class ThemeAssetVariant(models.Model):
    """One generated size or format of an asset (e.g. a 320 px WebP of the logo)."""

    asset = models.ForeignKey(ThemeAsset, on_delete=models.CASCADE, related_name="variants")
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    format = models.CharField(max_length=10, help_text="png, webp, avif, ico or svg.")
    purpose = models.CharField(max_length=40, blank=True, help_text="e.g. favicon-32 or 2x.")
    file = models.FileField(upload_to=variant_path)

    class Meta:
        ordering = ["asset", "format", "width"]

    def __str__(self):
        return f"{self.asset} {self.width}px {self.format}"
