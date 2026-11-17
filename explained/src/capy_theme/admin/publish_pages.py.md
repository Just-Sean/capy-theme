# src/capy_theme/admin/publish_pages.py

**What it is:** the theme admin's extra pages, all needing `publish_theme` where they change anything. Publishing itself is done with the buttons in `save_publish.py` (#273).

- **Revisions** (`<id>/revisions/`): every revision, and **compare** any two (`history.compare`).
- **Restore** (`<id>/revisions/<n>/restore/`): confirms, then republishes an old revision as a new one.

The Revisions and Restore pages find the theme with `save_publish.theme_or_404`, so a malformed id is a 404, not a server error (#275).
