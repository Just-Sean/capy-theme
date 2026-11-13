# tests/artifacts/test_daisyui_block.py

**What it tests:** Tests for the daisyUI theme block download (issue #55).

**Code it covers:** `src/capy_theme/artifacts/`

**Its 3 tests** (each name says what must hold):

- two blocks with every daisyui variable
- no published theme is 404
- the issue check tailwind builds it

Run just this file with `uv run pytest tests/artifacts/test_daisyui_block.py`.
