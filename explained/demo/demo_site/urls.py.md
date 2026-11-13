# demo/demo_site/urls.py

**What it is:** the demo's URL routes.

| URL | Goes to |
| --- | --- |
| `/` | `home.html`, the sample page |
| `/admin/` | Django's admin, where themes are managed |
| `/theme/...` | capy-theme's own URLs (`include("capy_theme.urls")`): the stylesheets, mode and theme-choice links, the editor's endpoints, the API and downloads |
| `/media/...` | Uploaded files, served by Django only because `DEBUG` is on. A real site serves these from its web server or storage. |

`path("theme/", include("capy_theme.urls"))` is the one line every project using capy-theme needs.
