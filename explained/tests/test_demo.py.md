# tests/test_demo.py

**What it tests:** that the demo site in `demo/` still works, so it can't break unnoticed. It runs the demo's own `manage.py` as a separate process with the demo's settings.

- the demo passes Django's system checks
- its home page renders (on a freshly migrated database)
- its header logo uses the theme's header height (no fixed size classes)
- its navbar has the mode toggle
