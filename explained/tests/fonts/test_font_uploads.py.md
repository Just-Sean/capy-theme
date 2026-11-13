# tests/fonts/test_font_uploads.py

**What it tests:** Tests for font uploads (issue #26).

**Code it covers:** `src/capy_theme/fonts/`

**Its 10 tests** (each name says what must hold):

- ttf woff and woff2 become woff2
- weight style and family are read from the font
- trimming keeps only the subset
- not trimming keeps everything
- a subset the font doesnt have is refused
- a renamed image is rejected
- too big is rejected
- codepoints
- the issue check upload a ttf and it renders
- the issue check renamed image is rejected in the admin

Run just this file with `uv run pytest tests/fonts/test_font_uploads.py`.
