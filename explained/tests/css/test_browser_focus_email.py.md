# tests/css/test_browser_focus_email.py

**What it tests:** Tests for browser color, focus color and email colors (issue #20).

**Code it covers:** `src/capy_theme/css/`

**Its 8 tests** (each name says what must hold):

- theme color follows the device with one tag per mode
- theme color uses an overridden background
- forced mode gives a single theme color
- focus outline rule is in the stylesheet
- focus uses primary when it stands out
- focus falls back to text color when primary is too faint
- hex colors for emails
- context has email colors

Run just this file with `uv run pytest tests/css/test_browser_focus_email.py`.
