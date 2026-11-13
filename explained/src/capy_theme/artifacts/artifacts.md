# src/capy_theme/artifacts/

**The theme as data for other code.** capy-theme applies the theme only to the page's own look. Everything else it produces (logos for email and print, icons, the sharing image, colors as hex, fonts) is **made available** here. A project or another module (email, app shell, PWA manifest, link-preview tags) does those jobs with it.

| File | Job |
| --- | --- |
| `__init__.py` | Exposes `get_artifacts` |
| `build.py` | `get_artifacts()`: everything published, as plain data |
| `api.py` | The public JSON API at `/theme/api.json` (plain Django view) |
| `api_drf.py` | The same API as a Django REST Framework view, for projects using DRF |
| `downloads.py` | `/theme/tokens.json` and `/theme/daisyui-theme.css` |
| `tokens.py` | The theme as W3C design tokens |
| `daisyui_block.py` | The theme as daisyUI theme blocks |
