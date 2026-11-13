# src/capy_theme/editor/preview.py

**What it is:** previewing **unsaved** values with exactly the code used for publishing, so what you see is what would go live.

- **`apply_changes(theme, data)`:** returns an **unsaved copy** of the theme with the editor's values applied.
  - The editor manages bases, colors, shape, fonts, type, images, logo heights and icon settings. Everything else (name, branding, mode, custom CSS) is kept.
  - Colors in any format are converted to OKLCH.
  - It validates everything (bases, the settings schema, fonts and images exist) and reports **every** problem at once.
  - It never changes the database.
- **`preview(theme, data)`:** for that copy, returns:
  - the CSS
  - every value in both modes, plus hex versions for the color pickers
  - the contrast report
  - the settings and bases
  - any external font stylesheets the page must link
