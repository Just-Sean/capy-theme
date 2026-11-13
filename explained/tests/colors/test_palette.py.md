# tests/colors/test_palette.py

**What it tests:** Tests for palette suggestions (issue #18).

**Code it covers:** `src/capy_theme/colors/`

**Its 10 tests** (each name says what must hold):

- three suggestions from a primary color
- complementary is the opposite hue
- logo colors most used first ignoring white
- logo without color gives no suggestion
- broken file gives no suggestion
- endpoint gives logo and primary suggestions
- endpoint without logo
- endpoint rejects a bad color
- endpoint saves nothing
- endpoint needs permission

Run just this file with `uv run pytest tests/colors/test_palette.py`.
