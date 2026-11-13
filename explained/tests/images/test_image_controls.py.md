# tests/images/test_image_controls.py

**What it tests:** Tests for uploading images in the admin and the live editor (issue #32).

**Code it covers:** `src/capy_theme/images/`

**Its 6 tests** (each name says what must hold):

- admin upload strips gps
- admin rejects a renamed text file
- editor upload
- editor rejects a renamed text file
- editor upload needs a file
- editor upload needs permission

Run just this file with `uv run pytest tests/images/test_image_controls.py`.
