# src/capy_theme/migrations/0011_remove_app_and_social_settings.py

**Data migration** (#143). It removes the `app` and `social` keys from themes' settings when capy-theme stopped serving a web app manifest and link-preview tags itself. It now exposes artifacts for other modules to do that instead. The sharing image itself stayed.
