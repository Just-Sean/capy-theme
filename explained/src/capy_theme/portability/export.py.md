# src/capy_theme/portability/export.py

**What it is:** `export_theme(theme)` returns a zip, `<slug>.capy-theme.zip`, with:

- **`theme.json`:**
  - the format version, and which capy-theme made it
  - the **draft's** name, slug, bases and settings
  - fonts and images referred to by keys (`font-3`, `image-7`), not database IDs, since IDs differ between sites
- **`fonts/`:** the font files used, with each font's details.
- **`images/`:** the uploaded original images used, with slot, mode and alt text.

Generated files (logo copies, icons) aren't included; they're made again on import and publish.
