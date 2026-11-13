# src/capy_theme/management/commands/theme_import.py

**`manage.py theme_import FILE [--publish] [--activate]`** imports an export zip as a new, unpublished draft (`import_theme`), with all the same checks as the admin's import.

- `--publish` publishes it too.
- `--activate` publishes it and makes it the site's theme.

Problems are shown as a readable error.
