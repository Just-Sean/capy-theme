# tests/admin/test_admin_tabs.py

**What it tests:** the tabs on the theme edit page.

**Code it covers:** `src/capy_theme/admin/tabs.py`, `theme_change_form.html`

**Its 11 tests** (each name says what must hold):

- every section has a tab
- only the color advanced and expert groups stay folded
- the page has its tabs in order
- tab ids come from their labels
- every section is still on the page with its old id
- sections are in their tabs
- folded sections open in their tab except color groups
- the tab script and stylesheet are loaded
- the add page has tabs too
- a section without a tab goes to more
- empty tabs are left out

The script itself (tab switching, keyboard, errors) has no automated tests: the project has no browser test setup. It's checked by hand.

Run just this file with `uv run pytest tests/admin/test_admin_tabs.py`.
