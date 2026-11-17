# src/capy_theme/editor/state.py

**What it is:** what the editor panel receives when it opens.

- **`editor_urls(theme)`:** the endpoint URLs.
- **`draft_state(theme, user, request)`:**
  - the draft's bases and settings (without custom CSS, which the editor doesn't edit)
  - its CSS, the live revision number, and whether there are unpublished changes
  - whether this user can publish, and whether it's already the site's theme (then there's no activate button, #273)
  - the theme's uploaded images
  - the current values and contrast
- **`controls()`:** what the panel offers, built from the same data files the admin uses, so the two always agree:
  - the base theme lists and the color groups
  - shape sizes with their limits and steps, and effects
  - every image slot with its limits, whether it takes SVG, its modes, and its help and empty text for each mode (the same text as the admin, from `images/slot_text.py`, #271)
  - icon settings and logo heights
  - font roles, type settings and the library's fonts
