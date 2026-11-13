# src/capy_theme/admin/inlines.py

**What it is:** the two lists inside the theme edit page.

- **`ThemeAssetInline`:** the theme's **uploaded images**, with a preview and details (size, type). New uploads go through `prepare_image` (the same checks as the editor). Existing images can't be edited, only added or deleted, because they're never changed after upload.
- **`ThemeRevisionInline`:** the **published revisions**, read-only (no add, change or delete), marking the live one.
