# src/capy_theme/migrations/0005_theme_logo.py

**Schema and data migration.** Themes get a single logo, and older revisions get an empty `logo` entry. It was later replaced by logo slots (0010). `images/logos.py` still reads that old single-logo key in old revisions.
