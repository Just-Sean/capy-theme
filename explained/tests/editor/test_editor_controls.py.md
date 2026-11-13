# tests/editor/test_editor_controls.py

**What it tests:** Tests for the editor's color and shape controls (issue #97).

The controls themselves are JavaScript (editor/controls/*.js), checked in headless Chrome while building. These tests cover the data the server gives them.

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 10 tests** (each name says what must hold):

- controls list bases colors and shape
- bases follow the project setting
- preview gives hex for every color picker
- state includes controls and current values
- mount loads the controls script
- controls script is bundled
- the page makes room for the open editor
- the components frame only loads a path on this site
- the file chooser looks like a button
- every shape size has a real step

Run just this file with `uv run pytest tests/editor/test_editor_controls.py`.
