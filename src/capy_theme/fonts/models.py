"""The font library: Font and its files (FontFile)."""

from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models

# These values go into CSS (and the admin's font previews) as they are, so only
# characters that can't end a string, a rule or a <style> block are allowed (#235).
# The same patterns are in portability/theme_file.schema.json, for imports.
FAMILY_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9 -]{0,99}$"
_NAME = r"""(?:[A-Za-z0-9_. -]+|"[A-Za-z0-9_. -]+"|'[A-Za-z0-9_. -]+')"""
FALLBACK_PATTERN = rf"^\s*{_NAME}(?:\s*,\s*{_NAME})*\s*$"
_RANGE = r"U\+[0-9A-Fa-f?]{1,6}(?:-[0-9A-Fa-f]{1,6})?"
UNICODE_RANGE_PATTERN = rf"^{_RANGE}(?:\s*,\s*{_RANGE})*$"

family_validator = RegexValidator(
    FAMILY_PATTERN, "Use letters, digits, spaces and hyphens only, e.g. Source Serif 4."
)
fallback_validator = RegexValidator(
    FALLBACK_PATTERN,
    'List font names separated by commas, e.g. ui-sans-serif, "Segoe UI", sans-serif. '
    "Names may use letters, digits, spaces, hyphens, dots and underscores.",
)
unicode_range_validator = RegexValidator(
    UNICODE_RANGE_PATTERN, "Use CSS unicode-range values, e.g. U+0000-00FF, U+0131."
)


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
        max_length=100,
        unique=True,
        validators=[family_validator],
        help_text="The font's name, e.g. Inter or Source Serif.",
    )
    source = models.CharField(max_length=20, choices=SOURCES, default="upload")
    fallback_stack = models.CharField(
        max_length=300,
        blank=True,
        validators=[fallback_validator],
        help_text="Fonts to use while this one loads or if it can't, e.g. "
        "ui-sans-serif, system-ui, sans-serif. Blank uses a sensible default for the role.",
    )
    license = models.TextField(blank=True, help_text="The font's license, or where to find it.")
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
        max_length=500,
        blank=True,
        validators=[unicode_range_validator],
        help_text="Optional CSS unicode-range for this subset.",
    )
    file = models.FileField(upload_to="capy_theme/fonts/", help_text="A WOFF2 font file.")

    class Meta:
        ordering = ["font", "weight", "style"]

    def __str__(self):
        return f"{self.font} {self.weight} {self.style} ({self.subset})"
