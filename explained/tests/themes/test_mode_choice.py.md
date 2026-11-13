# tests/themes/test_mode_choice.py

**What it tests:** Tests for choosing a mode (the view and cookie) and the mode settings (issue #46).

**Code it covers:** `src/capy_theme/themes/`

**Its 9 tests** (each name says what must hold):

- choosing a mode sets a long lived cookie and goes back
- choosing a mode wont redirect to another site
- unknown mode is not found
- choice isnt saved when switching is off
- cookie changes the next page
- form stores only non default mode settings
- form shows the current mode settings
- context has the mode
- mode settings are published like everything else

Run just this file with `uv run pytest tests/themes/test_mode_choice.py`.
