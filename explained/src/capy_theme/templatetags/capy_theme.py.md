# src/capy_theme/templatetags/capy_theme.py

**What it is:** every template tag a project uses. This is how capy-theme gets onto a project's pages.

| Tag | Where | Outputs |
| --- | --- | --- |
| `{% theme_html_attrs %}` | inside `<html ...>` | `data-theme="capy-light"` or `"capy-dark"` when a mode is forced |
| `{% theme_head %}` | inside `<head>` | font preloads, external font stylesheets, the theme stylesheet, custom CSS, browser-color tags, icons, the light/dark script (with the CSP nonce if Django's CSP is on), and the live editor for staff |
| `{% theme_logo slot="main" %}` | anywhere | the logo `<picture>`, or the site name if there's no logo; extra attributes go on the image |
| `{% theme_mode_toggle %}` | anywhere | Light / Dark / Auto buttons, if the theme allows switching |
| `{% theme_picker %}` | anywhere | links to choose an offered theme, or nothing if none are offered |
| `{% theme_artifacts as a %}` | anywhere | `get_artifacts()` for the template |
| `capy_get` filter | anywhere | looks up a dict key held in a variable |

Every tag outputs nothing (or just the editor) when no theme is published, so a fresh install doesn't break pages.

**About the CSP nonce:** Django's nonce counts as "false" until something reads it. The code checks `is not None` rather than its truth, so the nonce is always included.
