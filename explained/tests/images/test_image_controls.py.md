# tests/images/test_image_controls.py

**What it tests:** Tests for uploading images in the admin and the live editor (issue #32).

**Code it covers:** `src/capy_theme/images/`

**Its 9 tests** (each name says what must hold):

- admin upload strips gps
- admin rejects a renamed text file
- editor upload
- editor rejects a renamed text file
- editor upload needs a file
- editor upload needs permission
- admin refuses an oversized upload before reading it
- a header logo uploaded in the admin gets its smaller copies
- a sharing image uploaded in the admin gets its 1200 by 630 copy

The admin tests upload in a slot's own field on the theme page (#271).

Run just this file with `uv run pytest tests/images/test_image_controls.py`.
