# tests/themes/test_permissions.py

**What it tests:** Tests for theme permissions (issue #12).

**Code it covers:** `src/capy_theme/themes/`

**Its 9 tests** (each name says what must hold):

- permissions are declared
- designer can edit drafts
- designer sees no publish button
- designer direct publish request is refused
- designer sees no activate action
- designer direct activate request is refused
- publisher sees the publish button and can publish
- publisher can activate
- superusers can publish

Run just this file with `uv run pytest tests/themes/test_permissions.py`.
