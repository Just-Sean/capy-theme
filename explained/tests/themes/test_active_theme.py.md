# tests/themes/test_active_theme.py

**What it tests:** Tests for active theme selection (issue #7).

**Code it covers:** `src/capy_theme/themes/`

**Its 16 tests** (each name says what must hold):

- no active theme by default
- activating changes the active theme
- active theme comes with its live revision
- second call makes no database queries
- no active theme is cached too
- unpublished theme cant be activated
- publishing clears the cache
- changing the assignment clears the cache
- deleting the active theme leaves none active
- cache time defaults to 5 minutes and follows the setting
- only one default assignment per site
- get active theme accepts a request
- admin activate action
- admin refuses unpublished theme
- admin refuses more than one theme
- admin list shows which theme is active

Run just this file with `uv run pytest tests/themes/test_active_theme.py`.
