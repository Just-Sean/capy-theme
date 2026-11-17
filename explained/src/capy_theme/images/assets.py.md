# src/capy_theme/images/assets.py

**What it is:** storing checked images as a theme's assets, and telling which assets are in use (#271).

- **`ALT_MAX`:** alt text is at most 200 characters.
- **`store_asset(theme, slot, mode, clean, alt_text)`:** saves an image already checked by `uploads.prepare_image` as a new `ThemeAsset`, then makes its smaller copies (header logos) and the 1200 × 630 copy (sharing image), like every upload. Existing assets are never changed.
- **`where_used(theme, settings, asset)`:** where an image is in use, as short descriptions like "the draft's main logo (light)" or "the published theme's icon (dark)". It checks the draft's choices (`settings`, which may be unsaved) and the live revision. An empty list means it's free to delete.
- **`asset_data(asset)`:** an asset as JSON for the editor, including its file name.
