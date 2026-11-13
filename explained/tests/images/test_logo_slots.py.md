# tests/images/test_logo_slots.py

**What it tests:** Tests for logo slots: copies, choosing, fallbacks and the migration (issue #34).

**Code it covers:** `src/capy_theme/images/`

**Its 10 tests** (each name says what must hold):

- header logos get smaller copies in three formats
- jpeg logos fall back to jpeg
- other slots get no copies
- svg logos get no copies
- revision has the chosen images and their copies
- images only in the slot they were uploaded for
- fallbacks
- old revisions with a single logo still work
- admin offers every slot and header heights
- migration moves the old logo into the main slot

Run just this file with `uv run pytest tests/images/test_logo_slots.py`.
