# tests/admin/test_import_export_admin.py

**What it tests:** Tests for the theme admin's Export button and Import theme page (issue #54).

**Code it covers:** `src/capy_theme/admin/`

**Its 4 tests** (each name says what must hold):

- export button and download
- import needs the import permission
- import page imports a draft
- import page shows problems

Run just this file with `uv run pytest tests/admin/test_import_export_admin.py`.
