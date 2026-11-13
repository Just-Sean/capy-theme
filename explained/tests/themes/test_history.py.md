# tests/themes/test_history.py

**What it tests:** Tests for revision history: compare and restore (issue #44).

**Code it covers:** `src/capy_theme/themes/`

**Its 17 tests** (each name says what must hold):

- describe names every value
- compare shows exactly what changed
- compare identical revisions
- restore publishes the old revision as a new one
- restoring the live revision does nothing
- restore brings back the old logo
- restore skips images deleted since
- revisions page lists and compares
- revisions page defaults to the last two
- theme page links to revisions
- restore needs publish permission
- restore through the admin
- revisions page needs view or change permission
- restore explains a revision that can no longer be used
- restore explains a simultaneous publish
- revisions page without both revisions shows no comparison
- restoring the live revision says so

Run just this file with `uv run pytest tests/themes/test_history.py`.
