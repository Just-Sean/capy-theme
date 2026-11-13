# tests/themes/test_catalog.py

**What it tests:** Tests for the built-in daisyUI theme catalog (issue #4).

**Code it covers:** `src/capy_theme/themes/`

**Its 12 tests** (each name says what must hold):

- catalog has 35 themes each with all 28 values
- each theme is light or dark
- themes are in daisyui order
- catalog records its daisyui version
- themes cannot be changed through the catalog
- setting limits the list
- setting keeps daisyui order
- unknown theme in setting raises
- empty setting offers no themes
- parse js export reads objects and arrays with trailing commas
- build themes splits scheme from values in order
- build themes rejects mismatched order

Run just this file with `uv run pytest tests/themes/test_catalog.py`.
