# src/capy_theme/portability/theme_file.schema.json

**What it is:** the JSON Schema for an export zip's `theme.json`.

- **Required:** the format (`capy-theme-export/1`), the theme (name, slug, bases, settings, font roles, image slots), the fonts and the images.
- **Limits:** length limits, a slug pattern, at most 20 fonts, and so on.
- **Nothing extra:** keys it doesn't list are refused.

`importing.py` checks every import against it before reading anything else. The settings themselves are then checked against `settings.schema.json`.
