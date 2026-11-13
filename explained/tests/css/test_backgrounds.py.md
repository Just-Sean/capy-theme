# tests/css/test_backgrounds.py

**What it tests:** Tests for background images (issue #38).

**Code it covers:** `src/capy_theme/css/`

**Its 7 tests** (each name says what must hold):

- backgrounds are css variables per mode
- helper classes
- template values
- an old single logo never becomes a background
- svg patterns are allowed
- the issue check admin background shows on the demo page
- editor preview shows backgrounds straight away

Run just this file with `uv run pytest tests/css/test_backgrounds.py`.
