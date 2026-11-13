# tests/themes/test_publishing_drafts.py

**What it tests:** Tests for publishing a theme's draft as a revision (issue #12).

**Code it covers:** `src/capy_theme/themes/`

**Its 13 tests** (each name says what must hold):

- new theme is unpublished
- publish creates revision with who and when
- editing changes only the draft
- each publish adds a numbered revision
- publishing without changes is refused
- renaming needs no publish
- invalid draft cant be published
- saving a stale copy doesnt unpublish
- publish without a user
- snapshot is a copy not shared with the draft
- deleting a user keeps their revisions
- deleting a theme deletes its revisions
- two publishes cant get the same number

Run just this file with `uv run pytest tests/themes/test_publishing_drafts.py`.
