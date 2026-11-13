# tests/themes/test_publish_admin.py

**What it tests:** Tests for the admin's Publish page and revision list (issue #12).

**Code it covers:** `src/capy_theme/themes/`

**Its 10 tests** (each name says what must hold):

- edit page has publish button and status
- publish page shows confirmation with note
- publish page publishes with note
- publish page with no changes says so
- edit page lists revisions read only
- saving the edit form doesnt publish
- list shows live revision and unpublished changes
- publish page explains a simultaneous publish
- staff without change permission cant publish
- publish page explains an invalid draft

Run just this file with `uv run pytest tests/themes/test_publish_admin.py`.
