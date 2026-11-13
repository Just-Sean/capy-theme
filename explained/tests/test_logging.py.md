# tests/test_logging.py

**What it tests:** capy-theme logs its important events through its own loggers, all under `capy_theme` (issue #208):

- publishing (with the user's **ID, never their name**) and publishing with no user
- restoring a revision
- activating a theme, for every site or one domain
- importing a theme and importing a Google font
- Google Fonts being unreachable, logged as a warning

It also checks capy-theme sets up **no handlers** of its own, so the project's `LOGGING` decides where messages go.
