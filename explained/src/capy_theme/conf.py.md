# src/capy_theme/conf.py

**What it is:** the one place that lists every `CAPY_THEME_*` setting a project can put in its `settings.py`, with its default. All code reads settings through `conf.get(name)`, and a test checks the README's Settings table lists the same ones.

| Setting | Default | Controls |
| --- | --- | --- |
| `CAPY_THEME_BUILTIN_THEMES` | all | Which daisyUI themes can be bases |
| `CAPY_THEME_CACHE_SECONDS` | 300 | How long the active theme is cached |
| `CAPY_THEME_API` | `"auto"` | Plain Django or DRF view for the API |
| `CAPY_THEME_VISITOR_THEMES` | True | The visitor theme picker on/off |
| `CAPY_THEME_CUSTOM_CSS` | True | Custom CSS on/off |
| `CAPY_THEME_EDITOR_BUTTON` | True | The "Edit theme" corner button |
| `CAPY_THEME_FONT_MAX_BYTES` | 5 MB | Font upload limit |
| `CAPY_THEME_IMAGE_MAX_BYTES` | None | A lower cap on every image slot |
| `CAPY_THEME_ANIMATION_MAX_FRAMES` / `_SIZE` / `_PIXELS` | 500 / 2000 px / 50 million | Animated image limits |
| `CAPY_THEME_IMPORT_MAX_BYTES` | 50 MB | Theme import zip limit |

`positive_int(name)` is for safety limits. A value that isn't a positive whole number (0, None, text) is a configuration error, not a way to turn the limit off.
