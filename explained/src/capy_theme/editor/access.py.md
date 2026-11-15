# src/capy_theme/editor/access.py

**What it is:** the editor's permission rules.

- **`can_edit(user)`:** a logged-in, active staff user with `change_theme`.
- **`can_publish(user)`:** the same, plus `publish_theme`.
- **`requested_theme_id(request)`:** the id in `?edit=<id>`, or None. Only ASCII digits count. "²" passes Python's `isdigit()` but not `int()`, and it used to crash the page.
- **`editor_theme(request)`:** which theme to edit: `?edit=<id>` on the URL, else the active theme.
