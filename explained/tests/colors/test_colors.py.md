# tests/colors/test_colors.py

**What it tests:** Tests for color overrides (issue #14).

**Code it covers:** `src/capy_theme/colors/`

**Its 15 tests** (each name says what must hold):

- there are 20 colors in three groups
- labels
- schema accepts color overrides
- schema rejects bad overrides
- overrides are merged over the base
- light and dark are separate
- stylesheet uses the override and nothing else changes
- changing a color is an unpublished change
- form has a field for every color in both modes
- form stores only the colors set
- clearing every color removes them
- form rejects a bad color
- blank fields show the base color as a hint
- admin groups colors basic advanced expert
- admin page shows and saves colors

Run just this file with `uv run pytest tests/colors/test_colors.py`.
