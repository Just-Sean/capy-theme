# src/capy_theme/templates/capy_theme/editor/mount.html

**What it is:** what `{% theme_head %}` adds for staff who can edit:

- the editor's stylesheet (`editor.css`)
- `editor.js`, then each section script in `controls/`

The editor's settings ride as **data attributes on the script tag**: the theme's ID and name, every endpoint URL, the CSRF token, and whether to show the corner button. They go there because a `<div>` isn't allowed in `<head>`. The panel itself is built by the JavaScript. Visitors never get this template.
