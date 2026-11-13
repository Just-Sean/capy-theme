# tests/themes/test_base_changes.py

**What it tests:** Tests for the notice when daisyUI has changed or removed a theme's base (issue #78).

**Code it covers:** `src/capy_theme/themes/`

**Its 9 tests** (each name says what must hold):

- no notes when daisyui is unchanged
- no notes for unpublished theme
- note when daisyui changed a base
- note when daisyui removed a base
- publishing again clears the note
- a project setting limiting themes is not flagged
- admin page shows the note
- admin page shows the removed note
- admin list flags affected themes

Run just this file with `uv run pytest tests/themes/test_base_changes.py`.
