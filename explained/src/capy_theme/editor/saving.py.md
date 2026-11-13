# src/capy_theme/editor/saving.py

**What it is:**

- **`save_draft(theme, data)`:** applies the editor's values (validated by `apply_changes`) and saves the draft. Only the bases and the editor's settings change. Visitors see nothing until it's published.
- **`suggestions(theme, primary)`:** the "Suggest colors" sets: from the theme's main logo (if it's a raster image) and from the primary color.
