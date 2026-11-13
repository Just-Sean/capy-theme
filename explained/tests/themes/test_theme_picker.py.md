# tests/themes/test_theme_picker.py

**What it tests:** Tests for the visitor theme picker (issue #47).

**Code it covers:** `src/capy_theme/themes/`

**Its 13 tests** (each name says what must hold):

- the issue check switch between two allowed themes
- the issue check a theme not on the list cant be forced
- unpublished themes arent offered
- default clears the choice
- next must be this site
- without a request its the site theme
- project can turn visitor themes off
- picker lists site default and offered themes
- picker is empty without offered themes
- whole page uses the chosen theme
- offering a theme clears the cache
- admin field
- offering isnt an unpublished change

Run just this file with `uv run pytest tests/themes/test_theme_picker.py`.
