# src/capy_theme/images/icons.py

**What it is:** **every browser and home-screen icon**, made from the theme's one square icon image when the theme is **published**.

- **`make_icons(snapshot)`:** makes seven files (listed in `icons.json`) in `MEDIA_ROOT/capy_theme/icons/<id>/`:
  - `favicon.ico` (16, 32 and 48 px in one file)
  - `favicon.svg`: wraps the image, and switches to the dark icon in dark mode
  - `apple-touch-icon.png`: 180 px, never transparent
  - `icon-192.png`, `icon-512.png`
  - `icon-maskable-512.png`: the icon in the middle 80% on a solid background, for Android
  - `icon-monochrome-512.png`: white in the icon's shape

  It applies the icon's background color and padding settings.
- **The folder name** is a hash of the icon images and settings, so each revision keeps its icons and republishing the same icon reuses them. The files are written last-first, so a half-finished set never counts as done.
- **`head_links(snapshot)`:** the `<link>` tags `{% theme_head %}` outputs: the ICO, SVG, 192 px and Apple icons.
- **`icon_urls(snapshot)`:** every icon's URL, for artifacts. The 512, maskable and monochrome icons are for a web app manifest, which capy-theme doesn't serve itself.
- **`square_preview(...)`:** an on-the-fly preview for the Components view.
