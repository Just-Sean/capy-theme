# scripts/components.tailwind.css

**What it is:** the Tailwind input file for the stylesheet of the Components view and the live edit page, used by `build_components_css.py`.

**What it says:**

- `@import "tailwindcss" source(none);` imports Tailwind without scanning anything automatically.
- **`@source` lines scan only these templates:**
  - `components.html` and the `components/` sample templates
  - `live_edit.html` and `live_edit_components.html`
  - `mode_toggle.html` and `theme_picker.html`
- `@plugin` adds daisyUI from the demo's plugin file.

The result is only loaded inside the Components view's iframe and on the live edit page, so it never affects a project's own pages.
