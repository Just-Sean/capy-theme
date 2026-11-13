# src/capy_theme/editor/state.py

**What it is:** what the editor panel receives when it opens.

- **`editor_urls(theme)`:** the endpoint URLs.
- **`draft_state(theme, user, request)`:**
  - the draft's bases and settings (without custom CSS, which the editor doesn't edit)
  - its CSS, the live revision number, and whether there are unpublished changes
  - whether this user can publish
  - the theme's uploaded images
  - the visitor summary, the current values and contrast
- **`controls()`:** what the panel offers, built from the same data files the admin uses, so the two always agree:
  - the base theme lists and the color groups
  - shape sizes with their limits and steps, and effects
  - image slots with their limits, logo slots with fallbacks, icon settings and logo heights
  - font roles, type settings and the library's fonts
