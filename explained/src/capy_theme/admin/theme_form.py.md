# src/capy_theme/admin/theme_form.py

**What it is:** `ThemeForm`, the theme edit form.

**Its own fields:**

- name, slug
- light and dark base: only light themes offered for light, dark for dark
- site name, tagline, logo alt text
- default mode, "visitors can switch"
- "offered to visitors"

**The area files** (`PARTS`: colors, type, shape, images, custom CSS) add the rest.

**Saving:** `clean()` writes everything back into the theme's `settings`, storing only values that differ from the defaults. Blank means "use the base", so it's removed. Then each part writes its own area.
