# tests/editor/test_editor_access.py

**What it tests:** Tests for who gets the live editor, which theme it edits, and its state (issue #42).

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 12 tests** (each name says what must hold):

- staff with change permission can edit
- staff without change permission cant
- editors get the editor
- no editor without permission
- no editor without a theme
- edit parameter picks another theme
- state has the draft and its css
- state css matches publishing
- state is refused without permission
- viewing the state changes nothing
- visitors dont get the editor
- editor files are bundled

Run just this file with `uv run pytest tests/editor/test_editor_access.py`.
