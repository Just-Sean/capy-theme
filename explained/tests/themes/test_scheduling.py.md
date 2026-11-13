# tests/themes/test_scheduling.py

**What it tests:** Tests for theme scheduling (issue #48).

**Code it covers:** `src/capy_theme/themes/`

**Its 11 tests** (each name says what must hold):

- the issue check holiday theme only inside its dates
- the cache never outlives a schedule boundary
- overlapping schedules the latest start wins
- open ended schedules
- a visitors choice still wins
- scheduled assignments list
- validation
- admin schedules a theme
- admin needs a date
- admin offers only published themes
- scheduling needs publish permission

Run just this file with `uv run pytest tests/themes/test_scheduling.py`.
