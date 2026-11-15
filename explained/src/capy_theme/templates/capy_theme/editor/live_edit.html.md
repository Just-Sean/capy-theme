# src/capy_theme/templates/capy_theme/editor/live_edit.html

**The live edit page** (`/theme/live-edit/`, issue #229). It's a whole page of its own and doesn't extend the project's base template.

- **Stylesheets:** capy-theme's bundled daisyUI stylesheet (`editor/components.css`), then `{% theme_head %}`, which adds the theme's stylesheet and, for editors, the live editor.
- **Title and heading:** both name the theme being edited. The heading is screen-reader only.
- **Skip link:** a "Skip to the components" link that shows when focused.
- **Header** (it wraps on narrow screens):
  - the published logo, or the site name (or "Live edit"), as plain text, so it doesn't depend on the project's home page, with the tagline
  - `{% theme_mode_toggle %}` and the visitor theme picker
  - a link to the admin
- **Main:** every component (`live_edit_components.html`). A note appears when there are no themes yet, or when `?edit=` names a theme that doesn't exist.
- **Nothing inline,** so a strict Content Security Policy blocks nothing.
