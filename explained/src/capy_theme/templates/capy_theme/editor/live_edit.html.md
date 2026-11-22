# src/capy_theme/templates/capy_theme/editor/live_edit.html

**The live edit page** (`/theme/live-edit/`, issue #229). It's a whole page of its own and doesn't extend the project's base template.

- **Preview scheme:** a theme is a single scheme (light or dark), so `<html>` carries `data-theme="capy-<scheme>"` to preview the theme in its own scheme. `editor/controls/core.js` updates it if the base is changed, so switching a light base for a dark one re-themes the page. There's no light/dark/auto toggle (it would be meaningless for a single-scheme theme).
- **Stylesheets:** capy-theme's bundled daisyUI stylesheet (`editor/components.css`), then `{% theme_head %}`, which adds the theme's stylesheet and, for editors, the live editor.
- **Title and heading:** both name the theme being edited. The heading is screen-reader only.
- **Skip link:** a "Skip to the components" link that shows when focused.
- **Header** (it wraps on narrow screens):
  - the theme being edited, from its draft (#271): its logo, or the site name (or "Live edit"), as plain text, so it doesn't depend on the project's home page, with the tagline. The logo is marked so the editor previews logo changes there. Without a theme to edit, it shows the published theme.
  - **Switch theme:** every theme (unpublished ones marked), each a link to `?edit=<id>`; the one being edited is marked `aria-current`. It isn't the visitors' theme picker, so it doesn't change the visitor's theme (#269)
  - a link to the admin
- **Main:** every component (`live_edit_components.html`). A note appears when there are no themes yet, or when `?edit=` names a theme that doesn't exist.
- **Nothing inline,** so a strict Content Security Policy blocks nothing.
