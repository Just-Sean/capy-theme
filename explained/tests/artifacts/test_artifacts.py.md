# tests/artifacts/test_artifacts.py

**What it tests:** Tests for theme artifacts: what other modules get from capy-theme (issue #143).

**Code it covers:** `src/capy_theme/artifacts/`

**Its 7 tests** (each name says what must hold):

- none without a published theme
- the issue check every artifact without touching models
- urls are absolute with a request
- published values not the draft
- empty theme has empty artifacts
- template tag
- migration removes app and social settings

Run just this file with `uv run pytest tests/artifacts/test_artifacts.py`.
