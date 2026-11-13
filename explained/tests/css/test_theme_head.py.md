# tests/css/test_theme_head.py

**What it tests:** Tests for {% theme_head %}, {% theme_html_attrs %} and the theme context (issue #9).

**Code it covers:** `src/capy_theme/css/`

**Its 8 tests** (each name says what must hold):

- theme head links the active stylesheet
- theme head follows publishing
- theme head outputs nothing without an active theme
- theme head works without a request
- theme html attrs outputs nothing yet
- context has the live values
- context is none without an active theme
- context reaches every template

Run just this file with `uv run pytest tests/css/test_theme_head.py`.
