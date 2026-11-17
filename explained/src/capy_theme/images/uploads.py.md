# src/capy_theme/images/uploads.py

**What it is:** the gatekeeper for every image upload: from the editor, the admin and theme imports. It's the most security-sensitive file in the app.

- **`add_asset(theme, slot, mode, upload, alt_text)`:** checks the slot and mode, runs `prepare_upload`, then stores it with `assets.store_asset` (which makes logo variants or the sharing image).
- **`prepare_upload(upload, slot)`:** `prepare_image` for a Django upload. One that's too big is refused before it's read (#253). The admin's image slots use it too.

**`prepare_image(data, name, slot)`:**

1. **Size:** refused over the slot's limit (or `CAPY_THEME_IMAGE_MAX_BYTES`).
2. **Type from content, not name:**
   - Text starting with `<` can only be an SVG. It's refused for no-SVG slots, otherwise cleaned by `svg.py`.
   - Anything else must open in Pillow as PNG, JPEG, WebP or GIF, so a renamed text file is refused.
3. **Dimensions are checked before decoding,** so a huge image is never unpacked into memory. For GIFs, every frame's own position and size is read first (`gif_frames.py`). A frame reaching past the edges is refused.
4. **Animation limits** (`_check_animation`): at most 2000 px, 500 frames and 50 million pixels in all. A small file can otherwise decode to huge memory.
5. **A clean copy** (`_clean_copy`):
   - re-saved without EXIF, text chunks or comments, which removes camera details and GPS
   - photos turned upright first
   - color profiles kept
   - animated GIFs keep their frames, timing, looping, transparency and per-frame disposal
   - there's a workaround for a Pillow bug with identical frames

A damaged file becomes "That file isn't a supported image". Anything else, like running out of memory, is left as a real server error so it gets logged and noticed.

Storing an image and `asset_data` moved to `assets.py` (#271).
