# src/capy_theme/images/models.py

**What it is:** the two image models.

- **`ThemeAsset`:** one uploaded image belonging to a theme. It has a slot, a mode (light or dark), the cleaned file (stored under `MEDIA_ROOT/capy_theme/assets/<slot>/`), alt text, width, height, byte size and content type. **It's never edited after upload.** A new image is a new asset, so published revisions keep pointing at theirs.
- **`ThemeAssetVariant`:** a generated copy of an asset: a smaller logo in AVIF, WebP or PNG, or the cropped sharing image. It records width, height, format and purpose, and is stored in `.../<slot>/variants/`.
