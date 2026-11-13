# src/capy_theme/editor/access.py

**What it is:** the editor's permission rules.

- **`can_edit(user)`:** a logged-in, active staff user with `change_theme`.
- **`can_publish(user)`:** the same, plus `publish_theme`.
- **`editor_theme(request)`:** which theme to edit: `?edit=<id>` on the URL, else the active theme.
