"""The font library: Font and its files (FontFile)."""

from django.core.exceptions import ValidationError
from django.db import models


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
