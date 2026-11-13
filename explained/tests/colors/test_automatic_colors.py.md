# tests/colors/test_automatic_colors.py

**What it tests:** Tests for automatic text colors and background shades (issue #16).

**Code it covers:** `src/capy_theme/colors/`

**Its 9 tests** (each name says what must hold):

- the issue check dark primary gets light text and vice versa
- every colored element gets readable text
- text is readable on any color
- a text color set by hand is kept
- text colors of colors not overridden come from the base
- background shades and text follow an overridden background
- shades set by hand are kept
- very dark backgrounds get lighter shades
- nothing is worked out without overrides

Run just this file with `uv run pytest tests/colors/test_automatic_colors.py`.
