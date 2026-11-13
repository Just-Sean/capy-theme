# tests/images/test_icons.py

**What it tests:** Tests for icons and favicons (issue #35).

**Code it covers:** `src/capy_theme/images/`

**Its 12 tests** (each name says what must hold):

- publishing makes every icon
- favicon svg switches with a dark icon
- background and padding
- transparent by default but home screen icons are solid
- maskable icon keeps the icon in the safe zone
- monochrome icon is white in the icons shape
- the issue check head links
- no icon no links
- each revision keeps its icons
- bad icon settings are rejected
- admin icon fields
- editor offers icon controls

Run just this file with `uv run pytest tests/images/test_icons.py`.
