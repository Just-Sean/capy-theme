# src/capy_theme/admin/tabs.py

**What it is:** how the theme edit page's sections are grouped into tabs. Presentation only.

- **`THEME_TABS`:** the tabs in order (General, Branding, Fonts, Light colors, Dark colors, Shape and contrast, Images, Revisions, Advanced) and which sections or inline lists each holds.
- **`STAY_FOLDED`:** the colors' Advanced and Expert groups. They stay folded inside their tab; every other section opens.
- **`theme_tabs()`:** called by `ThemeAdmin.render_change_form`. It returns the tabs to draw, each with its sections (keeping each section's original number, so Django's HTML ids don't change) and inline lists. Each tab's id comes from its label (e.g. `capy-tab-light-colors`) and `order` is its place in the row. Empty tabs are left out, and a section that isn't listed lands in a final **More** tab, so nothing is ever lost.

The template wraps each tab's sections in a panel, and `static/capy_theme/admin/tabs.js` turns the panels into tabs.
