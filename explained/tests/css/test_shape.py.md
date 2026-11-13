# tests/css/test_shape.py

**What it tests:** Tests for shape and effects (issue #19).

**Code it covers:** `src/capy_theme/css/`

**Its 13 tests** (each name says what must hold):

- every daisyui shape value is covered
- shape values
- schema limits
- the issue check box radius 0 makes cards square
- shape applies to both modes
- unset shape comes from the base
- form stores only the shape values set
- form shows current values and base hints
- form rejects out of range values
- clearing shape removes it
- admin has a shape section
- admin size fields have real steps
- every arrow stop saves in the admin

Run just this file with `uv run pytest tests/css/test_shape.py`.
