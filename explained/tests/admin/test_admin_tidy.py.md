# tests/admin/test_admin_tidy.py

**What it tests:** Tests for the tidied admin form (issue #41).

**Code it covers:** `src/capy_theme/admin/`

**Its 5 tests** (each name says what must hold):

- sections are in a clear order
- every setting is reachable
- advanced parts are folded
- edit live opens the editor on the home page
- no edit live for view only staff

Run just this file with `uv run pytest tests/admin/test_admin_tidy.py`.
