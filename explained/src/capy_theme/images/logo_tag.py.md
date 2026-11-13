# src/capy_theme/images/logo_tag.py

**What it is:** the HTML and CSS behind `{% theme_logo %}`.

- **`logo_html(snapshot, slot, alt, attrs)`:**
  - **header slots:** a `<picture>` with AVIF and WebP sources and a PNG or JPEG fallback, with `srcset` from the variants and `sizes` from the header heights, so the browser picks the smallest file that fits
  - **light/dark:** if the slot has a dark image, both are output with classes, and the stylesheet shows the one for the current mode. Both are lazy-loaded, so only the visible one downloads.
  - **email and print slots:** a plain `<img>` of the light image, since email programs don't handle `<picture>`
  - extra attributes from the tag go on the `<img>`, e.g. `class="h-8"`
- **`logo_css(snapshot)`:** the stylesheet rules: `img.capy-logo` height (smaller on phones), and showing or hiding the light or dark logo per mode.
