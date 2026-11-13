# src/capy_theme/apps.py

**What it is:** the app's Django configuration (`CapyThemeConfig`).

- Its name and label are `capy_theme`, displayed as "Capy Theme" in the admin.
- **`default_auto_field = BigAutoField`** is set here rather than left to the project, so the app's migrations come out the same in every project.
- **`ready()`** runs when Django starts. It imports `themes/signals.py`, which connects the signals that clear the active-theme cache whenever a theme, revision or assignment changes.
