# src/capy_theme/portability/

**Moving a theme between sites**, e.g. from staging to production, as a zip.

| File | Job |
| --- | --- |
| `export.py` | A theme → zip bytes |
| `importing.py` | A zip → a new, unpublished draft theme, checked thoroughly |
| `theme_file.schema.json` | The schema the zip's `theme.json` must match |

Used by the admin's Export and Import buttons and the `theme_export` / `theme_import` commands.
