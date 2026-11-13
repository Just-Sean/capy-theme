# tests/css/test_accessibility.py

**What it tests:** Tests for device accessibility preferences (issue #49).

**Code it covers:** `src/capy_theme/css/`

**Its 3 tests** (each name says what must hold):

- reduce motion stops animations and transitions
- more contrast removes noise and depth and thickens borders
- the rules come after the theme values

Run just this file with `uv run pytest tests/css/test_accessibility.py`.
