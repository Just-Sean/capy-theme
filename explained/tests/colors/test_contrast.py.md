# tests/colors/test_contrast.py

**What it tests:** Tests for contrast warnings (issue #17).

**Code it covers:** `src/capy_theme/colors/`

**Its 7 tests** (each name says what must hold):

- ratings
- report covers every pair
- the issue check light gray on white fails aa
- rating shows next to each color in the form
- warnings dont stop saving or publishing
- admin shows the contrast table
- new theme has no ratings yet

Run just this file with `uv run pytest tests/colors/test_contrast.py`.
