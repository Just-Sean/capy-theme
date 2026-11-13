# src/capy_theme/themes/branding.py

**What it is:** `branding(revision)` returns the **published** site name, tagline, main logo URL (light) and logo alt text.

The alt text falls back from the image's own alt text, to the theme's logo alt text, to the site name. Used by the context processor, `{% theme_logo %}` and the artifacts.
