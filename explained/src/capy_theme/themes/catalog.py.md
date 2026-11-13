# src/capy_theme/themes/catalog.py

**What it is:** access to **daisyUI's built-in themes**, the bases every capy-theme theme starts from. It loads `builtin_themes.json` once.

- **`get_builtin_themes()`:** the themes this project offers, in daisyUI's order, as `BuiltinTheme` objects (name, light or dark, values). Limited by `CAPY_THEME_BUILTIN_THEMES` if the project sets it; a name that doesn't exist is a configuration error.
- **`builtin_values(name)`:** a copy of one theme's CSS variable values, or None. Not limited by the setting, because it's used to copy values into revisions.
- `DAISYUI_VERSION`: which daisyUI the data came from.
