# src/capy_theme/portability/importing.py

**What it is:** `import_theme(upload, keep_custom_css)` creates a **new, unpublished draft** from an export zip. An import is untrusted input, so everything is checked before anything is kept:

1. **It must be a zip.** Its total unpacked size must be under `CAPY_THEME_IMPORT_MAX_BYTES` (50 MB), which guards against "zip bombs".
2. **`theme.json`** must match `theme_file.schema.json`. Its patterns limit the file paths it may name to `fonts/...` and `images/...`, and only paths listed there are ever read from the zip.
3. **The bases and settings** are validated like any theme.
4. **Images** go through the same checks and cleaning as uploads.
5. **Font files** go through the same checks as font uploads. A font already in the library (same family) is reused.
6. **Name clashes:** if the name or slug exists, " (imported)" / "-imported" is added.
7. **Custom CSS** is kept unless `keep_custom_css=False` is passed. The admin's Import page passes it for users without `edit_custom_css`. The `theme_import` command always keeps it: anyone who can run commands on the server already has full access.

All of it runs in one database transaction. **If anything fails, nothing is kept**, and stored files are deleted again. The import is logged.
