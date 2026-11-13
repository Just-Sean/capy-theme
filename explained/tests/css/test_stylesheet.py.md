# tests/css/test_stylesheet.py

**What it tests:** Tests for the theme stylesheet (issue #8).

**Code it covers:** `src/capy_theme/css/`

**Its 13 tests** (each name says what must hold):

- stylesheet url is under theme
- stylesheet has variables for both modes
- stylesheet is cached by browsers for a year
- publishing changes the url and the old url still works
- unknown version is not found
- stylesheet uses the saved values not todays daisyui
- stylesheet survives a removed daisyui theme
- admin links to the live stylesheet
- migration fills in values for old revisions
- migration version matches the module
- stylesheet url includes the package version
- package version changes the url
- stylesheet is served with or without v

Run just this file with `uv run pytest tests/css/test_stylesheet.py`.
