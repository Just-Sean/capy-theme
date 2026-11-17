# tests/editor/test_editor_access.py

**What it tests:** Tests for who gets the live editor, which theme it edits, and its state (issue #42).

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 19 tests** (each name says what must hold):

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
- editor moves focus into the panel and back
- escape closes the editor
- escape in the components view closes only the view
- page behind a full width panel is inert
- save and publish keep focus on their button (after activating, focus goes to Save and publish)
- see it as a visitor is gone
- revert goes back to the saved draft

Run just this file with `uv run pytest tests/editor/test_editor_access.py`.
