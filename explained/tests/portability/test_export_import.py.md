# tests/portability/test_export_import.py

**What it tests:** Tests for exporting a theme and importing it on another site (issue #54).

**Code it covers:** `src/capy_theme/portability/ and the management commands`

**Its 9 tests** (each name says what must hold):

- the issue check same look after a reset and import
- export contents
- fonts already in the library are reused
- a name that exists gets imported added
- bad exports are rejected and nothing is kept
- paths outside the zip folders are rejected
- a bad image removes everything stored so far
- too big is rejected
- exports made before 1 0 still import

Run just this file with `uv run pytest tests/portability/test_export_import.py`.
