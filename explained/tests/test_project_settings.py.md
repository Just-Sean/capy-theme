# tests/test_project_settings.py

**What it tests:** the `CAPY_THEME_*` settings (issue #61).

- **The README lists every setting with its default,** matching `conf.py`, so the docs can't fall behind.
- Every setting has a default and is read through `conf`.
- **One test per setting, showing it really changes behavior:**
  - built-in themes
  - cache seconds
  - API mode
  - visitor themes
  - custom CSS
  - editor button
  - font size limit, image size limit, import size limit
  - the three animation limits
- The animation limits must be positive whole numbers (0, None and text are configuration errors).
