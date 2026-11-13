# tests/themes/test_multiple_sites.py

**What it tests:** Tests for serving several domains, each with its own theme (issue #60).

**Code it covers:** `src/capy_theme/themes/`

**Its 10 tests** (each name says what must hold):

- the issue check two hostnames show different themes
- other domains and no request use the theme for every site
- port and case dont matter
- a sites schedule wins on that site
- a site theme wins over a schedule for every site
- changing one site clears every sites cache
- only bare domains
- site themes admin
- site themes need the publish permission
- a schedule can be for one site

Run just this file with `uv run pytest tests/themes/test_multiple_sites.py`.
