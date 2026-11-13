# demo/templates/base.html

**What it is:** the demo's page layout, which other pages extend. It shows how a project puts capy-theme on its pages.

**capy-theme's tags in it:**

- `{% load tailwind_cli capy_theme %}` loads the tags.
- `<html ... {% theme_html_attrs %}>` adds `data-theme="capy-light"` or `"capy-dark"` when a mode is forced, so the page arrives in the right mode with no flash.
- `{% theme_head %}` in `<head>`, after `{% tailwind_css %}`, adds:
  - the published theme's stylesheet, plus font preloads and any external font stylesheets
  - custom CSS
  - browser-color meta tags and tab icons
  - the light/dark script
  - for staff who can edit, the live editor
- `class="... capy-bg-pattern"` on `<body>` shows the theme's background pattern image, if one is set.
- **The header:**
  - `{% theme_logo %}` shows the main logo, or the site name if there's no logo.
  - `{{ theme.site_name }}` and `{{ theme.tagline }}` come from the context processor.
  - `{% theme_mode_toggle %}` gives the Light / Dark / Auto buttons.
  - `{% theme_picker %}` is in a "Theme" dropdown, shown only when themes are offered to visitors.
- An Admin link, and `<main>` holding each page's content.
