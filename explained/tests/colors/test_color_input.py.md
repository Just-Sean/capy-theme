# tests/colors/test_color_input.py

**What it tests:** Tests for entering colors any common way (issue #15).

**Code it covers:** `src/capy_theme/colors/`

**Its 9 tests** (each name says what must hold):

- any common format is stored as oklch
- transparency is kept
- non colors are rejected
- hex for the picker
- the issue check three formats save and show as oklch
- widget has a color picker matching the value
- empty picker shows the base color
- admin page loads the picker script
- picker script is bundled

Run just this file with `uv run pytest tests/colors/test_color_input.py`.
