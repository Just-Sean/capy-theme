# tests/images/test_logo_tag.py

**What it tests:** Tests for {% theme_logo %} and the editor's logo choices (issue #34).

**Code it covers:** `src/capy_theme/images/`

**Its 8 tests** (each name says what must hold):

- the issue check phones get a smaller file
- header heights change sizes and css
- the issue check dark mode swaps the logo
- alt text from the image then the theme then the site name
- slot argument
- unknown slot is an error
- editor saves logo choices and heights
- editor rejects another themes image

Run just this file with `uv run pytest tests/images/test_logo_tag.py`.
