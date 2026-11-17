# src/capy_theme/static/capy_theme/admin/tabs.js

**What it is:** the script that turns the theme edit page's panels into tabs. Without it, the panels just follow each other and the page reads top to bottom.

- Builds a row of tab buttons in the order of `capy_theme.admin.tabs.THEME_TABS`.
- Works like standard tabs for keyboard and screen readers: arrow keys, Home and End move between tabs (the WAI-ARIA tabs pattern).
- Every section starts folded; it opens the ones with errors, so they can be seen.
- After a failed save, opens the first tab with an error and marks every tab with errors (⚠ plus "has errors" for screen readers).
- Remembers the open tab (by name) for this page in the browser's session storage, so "Save and continue editing" comes back to it.
- If keyboard focus was on a field that ends up in a hidden tab, it moves focus to the open tab. On the add page, where Django puts focus on Save because every field is folded, it moves focus to the open tab's first section title instead.

Loaded by `templates/capy_theme/admin/theme_change_form.html`.
