# src/capy_theme/management/commands/theme_import.py

**`manage.py theme_import FILE [--publish] [--activate]`** imports an export zip as a new, unpublished draft (`import_theme`), with the same checks as the admin's import. One difference: it always keeps the export's custom CSS, while the admin drops it for users without `edit_custom_css`. Anyone running commands on the server already has full access.

- `--publish` publishes it too.
- `--activate` publishes it and makes it the site's theme.

Problems are shown as a readable error.
