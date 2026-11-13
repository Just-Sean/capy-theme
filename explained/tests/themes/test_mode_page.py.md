# tests/themes/test_mode_page.py

**What it tests:** Tests for which mode a page uses, the toggle and the head script (issue #46).

**Code it covers:** `src/capy_theme/themes/`

**Its 14 tests** (each name says what must hold):

- default is auto and follows the device
- theme default mode forces a mode
- visitor choice wins over the default
- visitor choice is ignored when switching is off
- unknown cookie value is ignored
- no attributes without an active theme
- toggle has three links and marks the current mode
- toggle is hidden when switching is off
- toggle is hidden without an active theme
- head script applies the mode before the page draws
- head script knows when switching is off
- head script carries the csp nonce
- head script has no nonce without csp
- head script and csp header share the real nonce

Run just this file with `uv run pytest tests/themes/test_mode_page.py`.
