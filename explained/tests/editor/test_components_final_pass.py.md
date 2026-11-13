# tests/editor/test_components_final_pass.py

**What it tests:** The Components view's final pass (issue #62): every editor setting shows there.

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 8 tests** (each name says what must hold):

- the issue check every editor setting changes the components view
- unsaved image choices show
- says which sites theme is showing
- text sample has every heading and the display font
- icon preview
- custom css for editors who may edit it
- others get only the published custom css
- selectors

Run just this file with `uv run pytest tests/editor/test_components_final_pass.py`.
