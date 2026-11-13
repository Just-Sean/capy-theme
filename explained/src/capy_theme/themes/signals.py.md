# src/capy_theme/themes/signals.py

**What it is:** one signal receiver. Whenever a Theme, ThemeRevision or ThemeAssignment is saved or deleted, it calls `active.clear_cache()`, so the next page load sees the change straight away. It's connected when the app starts (`apps.py`'s `ready()`).
