# src/capy_theme/themes/publishing.py

**What it is:** `publish(theme, user, note)`, the one way a draft goes live. It's used by the admin's publish buttons (theme page and theme list), the editor's publish buttons, restore, `theme_import --publish` or `--activate`, and the `theme_publish` command.

**What it does:**

1. Refuses with `NothingToPublish` if the draft matches the live revision.
2. Re-validates the draft: settings, fonts, images, bases.
3. Takes the draft's `snapshot()`.
4. **Makes the icons now** (favicons, app icons), so pages only ever link to files.
5. In one database transaction: creates the next numbered `ThemeRevision` with its stylesheet hash, records who published it, and points `live_revision` at it.
6. Logs "Published theme 'x' as revision N (user ID 5)". It logs an ID, never a name.

**`publish_and_activate(theme, user, note)`** (#273): publishes, then makes the theme the default theme (`active.activate`). If there's nothing new to publish, it still activates and returns None. A theme that was never published raises `NotPublished`.

**`NOTE_MAX`** (2,000): the longest note kept with a revision. The admin and the editor cut notes to it.
