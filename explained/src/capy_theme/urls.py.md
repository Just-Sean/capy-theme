# src/capy_theme/urls.py

**What it is:** the app's URL routes. A project includes them with `path("theme/", include("capy_theme.urls"))`, so all of these sit under `/theme/`.

| URL | What |
| --- | --- |
| `mode/<light/dark/auto>/` | Sets the visitor's mode cookie and goes back (the no-JavaScript toggle) |
| `choose/<slug>/` | Sets the visitor's theme choice cookie |
| `editor/<id>/state/`, `preview/`, `suggestions/`, `save/`, `upload/`, `publish/` | The live editor's JSON endpoints (staff only) |
| `editor/<id>/components/`, `icon-preview.png`, `custom.css` | The Components view and its helpers (staff only) |
| `editor/visitor-view/` | "See it as a visitor" data (staff only) |
| `api.json` | The public JSON API |
| `tokens.json`, `daisyui-theme.css` | Downloads: design tokens, daisyUI theme blocks |
| `custom/<version>.css` | A revision's custom CSS |
| `<version>.css` | A revision's theme stylesheet |

The API's view (plain Django or DRF) is chosen once, when the URLs load (`api_view()`). The stylesheet route comes last because it matches any `<something>.css`.
