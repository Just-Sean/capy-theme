# src/capy_theme/images/variants.py

**What it is:** `make_variants(asset)` makes **smaller copies of header logos** when they're uploaded, so phones download small files.

- It covers widths from 64 to 1280 px (about 25% apart) that are smaller than the image, plus the image's own width, capped at 2560.
- Each width is saved as **AVIF, WebP and PNG** (JPEG instead of PNG for JPEG logos).
- SVG logos and other slots are skipped, since an SVG scales by itself.

`theme_rebuild_images` can remake them.
