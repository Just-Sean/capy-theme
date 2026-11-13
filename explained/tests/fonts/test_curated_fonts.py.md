# tests/fonts/test_curated_fonts.py

**What it tests:** Tests for the curated font collection (issue #25).

**Code it covers:** `src/capy_theme/fonts/`

**Its 5 tests** (each name says what must hold):

- about 30 open license fonts are bundled
- the command adds them to the library
- running it again skips existing fonts
- the font list has a preview of each
- editor samples use each fonts stack

Run just this file with `uv run pytest tests/fonts/test_curated_fonts.py`.
