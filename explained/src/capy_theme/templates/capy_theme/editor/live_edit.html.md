# src/capy_theme/templates/capy_theme/editor/live_edit.html

**The live edit page** (`/theme/live-edit/`, issue #229). It's a whole page of its own and doesn't extend the project's base template.

- **Stylesheets:** capy-theme's bundled daisyUI stylesheet (`editor/components.css`), then `{% theme_head %}`, which adds the theme's stylesheet and, for editors, the live editor.
- **Header:**
  - the logo, or the site name (or "Live edit" before anything is published), with the tagline
  - `{% theme_mode_toggle %}` and the visitor theme picker
  - a link to the admin
- **Main:** every component (`live_edit_components.html`). With no themes yet, a note links to the admin to add one.
- **Nothing inline,** so a strict Content Security Policy blocks nothing.
