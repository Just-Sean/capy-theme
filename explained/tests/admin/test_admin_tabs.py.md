# tests/admin/test_admin_tabs.py

**What it tests:** the tabs on the theme edit page.

**Code it covers:** `src/capy_theme/admin/tabs.py`, `theme_change_form.html`

**Its 12 tests** (each name says what must hold):

- every section has a tab
- the page has its tabs in order
- tab ids come from their labels
- every section is still on the page with its old id
- sections are in their tabs
- the tab script and stylesheet are loaded
- the add page has tabs too
- a section without a tab goes to more
- empty tabs are left out
- every section and list renders foldable and starts folded
- tabs script opens only sections with errors
- tabs script moves focus off the save button on load

The script itself (tab switching, keyboard, errors) is only checked by reading its source: the project has no browser test setup. It's checked by hand.

Run just this file with `uv run pytest tests/admin/test_admin_tabs.py`.
