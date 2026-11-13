# tests/themes/test_theme_model.py

**What it tests:** Tests for the Theme model, its validation and its admin (issue #5).

**Code it covers:** `src/capy_theme/themes/`

**Its 17 tests** (each name says what must hold):

- new theme has defaults
- public ids are unique per theme
- name must be unique
- slug must be unique
- bases can be any theme of the matching type
- wrong or unknown base cant be saved
- base must be allowed by project setting
- empty settings are valid
- bad settings are rejected
- bad settings cant be saved
- bad settings cant be saved on update
- form offers only matching themes as bases
- form follows project setting
- form saves a valid theme
- form rejects too long branding
- admin list and add pages load
- admin creates a theme

Run just this file with `uv run pytest tests/themes/test_theme_model.py`.
