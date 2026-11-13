# tests/editor/test_editor_visitor_view.py

**What it tests:** Tests for the editor's "See it as a visitor" view and summary (issue #158).

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 9 tests** (each name says what must hold):

- the issue check visitors see the published theme
- the issue check a date inside a schedule
- an offered theme
- a bad date
- the summary
- the editor state has the summary and url
- needs the change permission
- theme at uses the same rules as the site
- the controls are loaded

Run just this file with `uv run pytest tests/editor/test_editor_visitor_view.py`.
