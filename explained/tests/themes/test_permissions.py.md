# tests/themes/test_permissions.py

**What it tests:** Tests for theme permissions (issue #12).

**Code it covers:** `src/capy_theme/themes/`

**Its 12 tests** (each name says what must hold):

- permissions are declared
- designer can edit drafts
- designer cant offer a theme to visitors
- publisher can offer a theme to visitors
- designer sees only save draft
- designer direct publish requests are refused
- designer pressing publish only saves the draft
- designer sees no row buttons
- designer direct activate request is refused
- publisher sees the publish buttons and can publish
- publisher can activate
- superusers can publish

Run just this file with `uv run pytest tests/themes/test_permissions.py`.
