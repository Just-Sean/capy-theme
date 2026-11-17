# tests/admin/test_audit_fixes.py

**What it tests:** the two fixes from the final pre-v1 security audit (#275): malformed theme ids on the Revisions, Restore and Export pages are 404s, not server errors, and the draft custom CSS is only for editors.

**Code it covers:** `src/capy_theme/admin/save_publish.py` (`theme_or_404`), `admin/publish_pages.py`, `admin/import_export.py`, `editor/custom_css_view.py`

**Its 4 tests** (each name says what must hold):

- a malformed or missing id is not found
- the pages still work for a real theme
- the pages still need their permissions
- the draft custom css is only for editors

Run just this file with `uv run pytest tests/admin/test_audit_fixes.py`.
