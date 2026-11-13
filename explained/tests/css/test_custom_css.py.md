# tests/css/test_custom_css.py

**What it tests:** Tests for custom CSS (issue #59).

**Code it covers:** `src/capy_theme/css/`

**Its 11 tests** (each name says what must hold):

- published custom css is linked after the theme stylesheet
- the issue check switched off it isnt loaded
- empty custom css isnt linked
- it needs publishing like everything else
- too long is rejected
- the issue check without the permission it cant be seen or changed
- with the permission it can be edited
- the editor never receives it
- revision comparison shows only a summary
- imports drop it unless the importer may edit it
- an empty custom css isnt stored

Run just this file with `uv run pytest tests/css/test_custom_css.py`.
