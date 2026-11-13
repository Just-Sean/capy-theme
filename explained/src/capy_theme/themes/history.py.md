# src/capy_theme/themes/history.py

**What it is:** revision history.

- **`describe(snapshot)`:** turns a revision into readable rows: "Light base", "Light color: Primary", "Shape: Box corner radius", each image, branding, mode. Custom CSS shows only on/off and length, never its content.
- **`compare(older, newer)`:** the rows that differ. This is the admin's revision comparison.
- **`restore(theme, revision)`:** copies an old revision into the draft and **publishes it as a new revision** noted "Restored revision N". History is never rewritten. Images deleted since are dropped so the restore still works. Logged.
