# src/capy_theme/migrations/0004_revision_values_and_css_version.py

**Schema and data migration.** Revisions start storing their base themes' **full values**, not just names, so daisyUI updates can't change a published theme. Each revision also gets a `css_version` (the stylesheet's hash name). For revisions published before this, it fills both in. Its hashing must stay in step with `css/stylesheet.py`'s `css_version`.
