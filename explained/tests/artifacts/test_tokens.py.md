# tests/artifacts/test_tokens.py

**What it tests:** Tests for the design tokens download (issue #53).

**Code it covers:** `src/capy_theme/artifacts/`

**Its 6 tests** (each name says what must hold):

- the issue check validates against the format schema
- the schema does catch mistakes
- download headers
- values
- gray colors have no hue
- no published theme is 404

Run just this file with `uv run pytest tests/artifacts/test_tokens.py`.
