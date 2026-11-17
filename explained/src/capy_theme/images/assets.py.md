# src/capy_theme/images/assets.py

**What it is:** storing checked images as a theme's assets, and telling which assets are in use (#271).

- **`ALT_MAX`:** alt text is at most 200 characters.
- **`store_asset(theme, slot, mode, clean, alt_text)`:** saves an image already checked by `uploads.prepare_image` as a new `ThemeAsset`, then makes its smaller copies (header logos) and the 1200 × 630 copy (sharing image), like every upload. Existing assets are never changed.
- **`revisions_of(theme)`:** the theme's revisions (number, the images they chose, whether live), loaded once for checking many images. Only the images part of each snapshot is read.
- **`where_used(theme, settings, asset, revisions)`:** where an image is in use, as short descriptions like "the draft's main logo (light)", "the published theme's icon (dark)" or "3 earlier revisions" (earlier revisions are counted, not listed). It checks the draft's choices (`settings`, which may be unsaved) and every revision, because restoring a revision needs its images. Choices a slot can't have (an old dark email logo) don't count. An empty list means it's free to delete.
- **`refusal(theme, settings, asset, revisions)`:** why an image can't be deleted and what to do, or "" if it can be. If only the draft uses it: choose another image (or None) and save, then delete it. If it has been published (live or an earlier revision), it can't be deleted at all, since published versions keep their images, and the message says so rather than suggesting steps that can't work.
- **`asset_data(asset)`:** an asset as JSON for the editor, including its file name.
