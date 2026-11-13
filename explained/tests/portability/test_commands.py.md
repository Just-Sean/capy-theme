# tests/portability/test_commands.py

**What it tests:** Tests for the management commands (issue #56).

**Code it covers:** `src/capy_theme/portability/ and the management commands`

**Its 7 tests** (each name says what must hold):

- the issue check a fresh install themed from the command line
- export default file name
- import publish without activating
- import reports problems
- publish and activate
- unknown slugs
- rebuild images remakes copies and icons

Run just this file with `uv run pytest tests/portability/test_commands.py`.
