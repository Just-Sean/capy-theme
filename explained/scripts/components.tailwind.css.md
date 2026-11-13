# scripts/components.tailwind.css

**What it is:** the Tailwind input file for the Components view's stylesheet, used by `build_components_css.py`.

**What it says:**

- `@import "tailwindcss" source(none);` imports Tailwind without scanning anything automatically.
- `@source` lines scan only `components.html` and the `components/` sample templates.
- `@plugin` adds daisyUI from the demo's plugin file.

The result is only loaded inside the Components view's iframe, so it never affects the page being edited.
