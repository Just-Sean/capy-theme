# src/capy_theme/fonts/models.py

**What it is:** the font library's two models.

- **`Font`:**
  - `family` (unique, e.g. "Inter")
  - `source`: system, bundled, upload, google or external
  - `fallback_stack`: fonts used while it loads; blank means a default for the role
  - `license` notes
  - `stylesheet_url`: external fonts only, and it must be https; other sources mustn't have one
- **`FontFile`:** one WOFF2 file of a font, with its weight (100–900), style (normal or italic), character subset and optional `unicode-range`. Stored under `MEDIA_ROOT/capy_theme/fonts/`.

Themes refer to fonts by ID in their settings. Publishing copies the font's details into the revision, so editing the library later can't change a published theme.
