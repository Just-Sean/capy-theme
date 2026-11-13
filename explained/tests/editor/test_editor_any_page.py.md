# tests/editor/test_editor_any_page.py

**What it tests:** Tests for editing on any page (issue #43).

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 7 tests** (each name says what must hold):

- editors get the editor on any page
- visitors and other staff dont
- non staff with permission dont
- edit parameter works on any page
- editor works without an active theme when editing one
- corner button can be turned off
- a page has one editor

Run just this file with `uv run pytest tests/editor/test_editor_any_page.py`.
