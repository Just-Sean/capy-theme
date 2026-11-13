# tests/themes/test_branding.py

**What it tests:** Tests for site name, tagline and main logo (issue #10).

**Code it covers:** `src/capy_theme/themes/`

**Its 15 tests** (each name says what must hold):

- form stores branding in settings
- form shows current values and blank removes them
- form chooses the main logo
- form only offers this themes images for the slot
- revision keeps its logo after the logo is replaced
- a theme cant choose another themes image
- changing branding is an unpublished change
- logo tag outputs the logo with alt text
- logo alt text falls back to the site name
- logo tag shows the site name without a logo
- logo tag outputs nothing without logo or site name
- logo tag outputs nothing without an active theme
- logo tag uses published values not the draft
- context has branding
- admin shows branding fields and read only settings

Run just this file with `uv run pytest tests/themes/test_branding.py`.
