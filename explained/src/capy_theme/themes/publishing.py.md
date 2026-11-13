# src/capy_theme/themes/publishing.py

**What it is:** `publish(theme, user, note)`, the one way a draft goes live. It's used by the admin's Publish page, the editor's Publish button, restore, imports with `--activate`, and the `theme_publish` command.

**What it does:**

1. Refuses with `NothingToPublish` if the draft matches the live revision.
2. Re-validates the draft: settings, fonts, images, bases.
3. Takes the draft's `snapshot()`.
4. **Makes the icons now** (favicons, app icons), so pages only ever link to files.
5. In one database transaction: creates the next numbered `ThemeRevision` with its stylesheet hash, records who published it, and points `live_revision` at it.
6. Logs "Published theme 'x' as revision N (user ID 5)". It logs an ID, never a name.
