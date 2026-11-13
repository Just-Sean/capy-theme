# src/capy_theme/migrations/

**Database migrations:** Django's step-by-step record of how capy-theme's tables were created and changed. A project applies them with `manage.py migrate`. **Never edit an existing migration.** Each change to the models gets a new one, made with:

    uv run django-admin makemigrations capy_theme --settings=tests.settings --pythonpath=.

Some are **data migrations** (`RunPython`) that move existing data along when the shape of the data changed. Those keep their own frozen copies of any data they need, so later code changes can't break them. Ruff skips this folder, and test coverage doesn't count it.

| Migration | Does |
| --- | --- |
| 0001 | Creates `Theme` |
| 0002 | Creates `ThemeRevision`, `Theme.live_revision`, the unique revision number rule |
| 0003 | Creates `ThemeAssignment` (which theme is active, per site, with schedule dates) |
| 0004 | Revisions store their bases' full values and get a `css_version` (data migration) |
| 0005 | Themes get a logo; old revisions get an empty logo (data migration) |
| 0006 | The extra permissions (publish, custom CSS, import) |
| 0007 | Creates `Font` and `FontFile` |
| 0008 | Adds the 13 system font stacks to the library (data migration) |
| 0009 | Creates `ThemeAsset` and `ThemeAssetVariant` |
| 0010 | Moves each theme's single logo into the main logo slot (data migration) |
| 0011 | Removes the old web app manifest and link-preview settings (data migration, #143) |
| 0012 | Adds `Theme.offered_to_visitors` |
| 0013 | The `ScheduledTheme` admin view (a proxy model) |
| 0014 | The `SiteTheme` admin view (a proxy model) |
| 0015 | Renames `Font.licence` to `Font.license`, keeping the values (#199) |

`__init__.py` (empty) makes the folder a package. `__pycache__/` is a build artifact.
