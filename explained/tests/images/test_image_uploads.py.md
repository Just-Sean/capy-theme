# tests/images/test_image_uploads.py

**What it tests:** Tests for checking and cleaning uploaded images (issue #32).

**Code it covers:** `src/capy_theme/images/`

**Its 15 tests** (each name says what must hold):

- the issue check gps is removed
- the issue check renamed text file is rejected
- a truncated image is rejected
- an unsupported format is rejected
- the type comes from the content not the name
- photos are turned upright before the exif goes
- png text chunks are removed and transparency kept
- size limit per slot
- pixel limit per slot
- every slot has a label limit and help
- add asset stores a clean copy
- add asset rejects unknown slots and modes
- an image that only breaks when decoded is rejected
- gif comments are removed
- other save errors arent hidden

Run just this file with `uv run pytest tests/images/test_image_uploads.py`.
