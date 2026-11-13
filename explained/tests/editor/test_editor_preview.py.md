# tests/editor/test_editor_preview.py

**What it tests:** Tests for the editor's draft preview endpoint (issue #96).

**Code it covers:** `src/capy_theme/editor/ and the editor's static files`

**Its 12 tests** (each name says what must hold):

- preview returns css values and contrast
- derived values match what publishing would produce
- any color format is accepted
- bases and shape can change
- preview writes nothing
- invalid values are listed
- bad json is refused
- only post
- refused without permission
- csrf is required
- apply changes leaves the theme alone
- mount passes the preview url and csrf token

Run just this file with `uv run pytest tests/editor/test_editor_preview.py`.
