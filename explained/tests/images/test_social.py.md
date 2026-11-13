# tests/images/test_social.py

**What it tests:** Tests for the social sharing image (issue #37; tags removed in #143).

**Code it covers:** `src/capy_theme/images/`

**Its 7 tests** (each name says what must hold):

- sharing image is cropped to 1200 by 630
- transparent parts become white
- svg isnt accepted for sharing
- theme head outputs no link preview tags
- admin sharing image field
- editor offers the sharing image slot
- old app and social settings are rejected

Run just this file with `uv run pytest tests/images/test_social.py`.
