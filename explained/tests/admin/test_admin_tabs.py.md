# tests/admin/test_admin_tabs.py

**What it tests:** the tabs on the theme edit page.

**Code it covers:** `src/capy_theme/admin/tabs.py`, `theme_change_form.html`

**Its 13 tests** (each name says what must hold):

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
- tabs script opens no sections
- tabs script moves focus off the save button on load
- a failed save shows the section with the error

The script itself (tab switching, keyboard, focus) can't run here, since the project has no browser test setup: the tests only check its source, and its behavior is checked by hand.

Run just this file with `uv run pytest tests/admin/test_admin_tabs.py`.
