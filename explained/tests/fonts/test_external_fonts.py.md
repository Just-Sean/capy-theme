# tests/fonts/test_external_fonts.py

**What it tests:** Tests for external font stylesheets (issue #28).

**Code it covers:** `src/capy_theme/fonts/`

**Its 5 tests** (each name says what must hold):

- external fonts need an https stylesheet
- other fonts cant have a stylesheet
- the stylesheet is linked and the family used
- each stylesheet once
- the editor gets the stylesheets to link

Run just this file with `uv run pytest tests/fonts/test_external_fonts.py`.
