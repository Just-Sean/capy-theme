# tests/admin/test_admin_tabs_unchanged.py

**What it tests:** that the tabs on the theme edit page are presentation only: the page submits the same fields, and saving, uploads, errors and permissions work as before.

**Code it covers:** `src/capy_theme/admin/tabs.py`, `theme_change_form.html`

**Its 15 tests** (each name says what must hold):

- the same form controls as the stock admin page (change and add pages): the tabbed page has exactly the fields Django's normal edit page has
- no duplicate ids on the tabbed page
- both inlines keep their management forms
- the form is still multipart for image uploads
- an image uploaded from the images tab is saved
- an inline error is inside the images tab
- a field error is inside its own tab
- a round trip save from the tabbed page succeeds
- no custom css section or field without the permission
- custom css section with the permission (with the setting on and off)
- view only staff see tabs and cannot save
- no section lands in the more tab
- the add page has no revisions or stray tabs

Run just this file with `uv run pytest tests/admin/test_admin_tabs_unchanged.py`.
