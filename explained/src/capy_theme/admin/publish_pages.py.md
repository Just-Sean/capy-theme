# src/capy_theme/admin/publish_pages.py

**What it is:** the theme admin's extra pages, all needing `publish_theme` where they change anything.

- **Publish** (`<id>/publish/`):
  - a confirmation page showing what's live now, with an optional note
  - calls `publish()`
  - says "Nothing to publish" if the draft matches, and handles someone else publishing at the same moment
- **Revisions** (`<id>/revisions/`): every revision, and **compare** any two (`history.compare`).
- **Restore** (`<id>/revisions/<n>/restore/`): confirms, then republishes an old revision as a new one.
