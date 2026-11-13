# tests/fonts/test_system_fonts.py

**What it tests:** Tests for the system font stacks (issue #24).

**Code it covers:** `src/capy_theme/fonts/`

**Its 4 tests** (each name says what must hold):

- the migration adds every stack
- system sans downloads no font files
- stacks are used as given
- editor and admin list them

Run just this file with `uv run pytest tests/fonts/test_system_fonts.py`.
