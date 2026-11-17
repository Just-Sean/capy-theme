# src/capy_theme/images/assets.py

**What it is:** storing checked images as a theme's assets, and telling which assets are in use (#271).

- **`ALT_MAX`:** alt text is at most 200 characters.
- **`store_asset(theme, slot, mode, clean, alt_text)`:** saves an image already checked by `uploads.prepare_image` as a new `ThemeAsset`, then makes its smaller copies (header logos) and the 1200 × 630 copy (sharing image), like every upload. Existing assets are never changed.
- **`revisions_of(theme)`:** the theme's revisions (number, snapshot, whether live), loaded once for checking many images.
- **`where_used(theme, settings, asset, revisions)`:** where an image is in use, as short descriptions like "the draft's main logo (light)", "the published theme's icon (dark)" or "revision 3's main logo (light)". It checks the draft's choices (`settings`, which may be unsaved) and every revision, because restoring a revision needs its images. Choices a slot can't have (an old dark email logo) don't count. An empty list means it's free to delete.
- **`refusal(theme, settings, asset, revisions)`:** why an image can't be deleted and what to do instead (choose another image or None and save, then publish if the published theme uses it; an earlier revision's image can't be deleted), or "" if it can be.
- **`asset_data(asset)`:** an asset as JSON for the editor, including its file name.
