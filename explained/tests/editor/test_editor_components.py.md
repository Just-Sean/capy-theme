# tests/editor/test_editor_components.py

**What it tests:** Tests for the live editor's Components view (issues #155 and #158).

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 8 tests** (each name says what must hold):

- every component in light and dark
- ids differ between light and dark
- only framed by the same site
- needs the change permission
- the editor knows where it is
- bundled stylesheet has the components
- the showcase is gone
- images section shows the saved drafts logos

Run just this file with `uv run pytest tests/editor/test_editor_components.py`.
