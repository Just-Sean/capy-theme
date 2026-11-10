# Changelog

## 0.1.0

The foundation: themes exist, one is live, and every page uses it. Publishing,
history and permissions work.

- **Built-in theme catalogue:** daisyUI 5.7.50's 35 themes and their 28 values,
  generated from the daisyUI package by `scripts/generate_builtin_themes.py`.
  `CAPY_THEME_BUILTIN_THEMES` limits which are offered.
- **Theme model:** name, slug, light and dark base, and `settings` overrides,
  validated against `settings.schema.json`. Admin list and form.
- **Revisions and publishing:** edits change only the draft. Publish (with an
  optional note) saves a numbered revision with who and when. Revisions store
  their base themes' full values, so a daisyUI update can't change a published
  theme. The admin flags themes whose base daisyUI has changed or removed.
- **Active theme:** an Activate action. `get_active_theme()` is cached for
  `CAPY_THEME_CACHE_SECONDS` (default 300) and cleared on any change.
- **Theme stylesheet:** `/theme/<version>.css`, cached by browsers for a year.
  Light values by default, dark in dark mode, plus `capy-light`/`capy-dark` rules
  to force a mode. Links carry `?v=<capy-theme version>`.
- **Template tags and context:** `{% theme_head %}`, `{% theme_html_attrs %}`
  (empty until the light/dark toggle), `{% theme_logo %}`, and a `theme`
  context variable with the published values.
- **Branding:** site name, tagline, and a main logo upload with alt text.
- **Theme showcase:** `/theme/showcase/`, every component in light and dark side
  by side. `CAPY_THEME_SHOWCASE` (`staff`, `public`, `off`) and
  `CAPY_THEME_BASE_TEMPLATE`.
- **Permissions:** `publish_theme` (publish, activate), `edit_custom_css` and
  `import_theme`.
- **Dependencies:** Django 6.1, jsonschema, Pillow.
