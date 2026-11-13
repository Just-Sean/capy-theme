# src/capy_theme/management/commands/capy_theme_add_fonts.py

**`manage.py capy_theme_add_fonts`** adds the 30 bundled fonts (listed in `fonts/curated.json`) to the font library.

- It copies each bundled WOFF2 file into the project's **media storage**, so bundled fonts work like uploaded ones on any storage (local disk or S3), and creates the Font and FontFile rows.
- Fonts already in the library (same family name) are skipped, so it's safe to run again.
