# src/capy_theme/images/slot_text.py

**What it is:** how each image slot is described to people. The admin and the live editor both use it, so they always say the same thing (#271).

- **`limits_text(slot)`:** the size limit and file types, e.g. "Up to 2 MB and 4000 px, PNG, JPEG, WebP, GIF or SVG."
- **`help_text(slot, mode)`:** for light, what the slot is for (from `slots.json`) plus its limits. For dark, that it's the dark mode version and that leaving it empty uses the light image.
- **`empty_text(slot, mode)`:** what a slot with no image shows:
  - dark: the light one is used in dark mode too
  - main logo: the site name is shown instead
  - other logos: the main logo is used
  - anything else: "No image."
