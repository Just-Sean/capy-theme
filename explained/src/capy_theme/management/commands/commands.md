# src/capy_theme/management/commands/

capy-theme's command-line commands. Run them with `uv run python manage.py <name>` (in the demo: `demo/manage.py`). They let a theme be moved, published and set up without the admin, e.g. in deploy scripts.

| Command | Does |
| --- | --- |
| `theme_export <slug>` | Save a theme as an export zip |
| `theme_import FILE [--publish] [--activate]` | Import a zip as a draft, optionally publish and make it the site's theme |
| `theme_publish <slug> [--note] [--activate]` | Publish a theme's draft |
| `theme_rebuild_images [<slug>]` | Remake logo copies, sharing crops and icons |
| `capy_theme_add_fonts` | Add the 30 bundled fonts to the library |
