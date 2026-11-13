# src/capy_theme/themes/validation.py

**What it is:** checks for theme data.

- **`validate_settings(value)`:** checks a theme's settings against `settings.schema.json` with the `jsonschema` package, and raises one ValidationError listing **every** problem with its location (e.g. `colors/light/primary: ...`). The schema is loaded once. Used on every theme save, by the forms, the editor and imports.
- **`validate_base(name, scheme)`:** the base must be an offered built-in theme of the right kind (a light base for light).
