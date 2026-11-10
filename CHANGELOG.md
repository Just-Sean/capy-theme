# Changelog

## 0.2.0

Colours and shape: every colour and shape value can be overridden, with readable
text guaranteed.

- **Colour overrides:** any of the 20 daisyUI colours, separately for light and
  dark, in `settings["colors"]`. Admin fields grouped Basic / Advanced / Expert;
  blank fields use (and show) the base theme's colour.
- **Colour input:** hex, rgb(), hsl(), oklch() or colour names, stored as OKLCH
  (ColorAide), with the browser's colour picker beside each field.
- **Automatic text colours and background shades:** readable `-content` colours
  for overridden colours (WCAG AA, white/black fallback), and base-200, base-300
  and base-content from an overridden background.
- **Contrast warnings:** WCAG ratings (fail, AA, AAA) for every colour pair, next
  to each colour field and in a table. Warnings only.
- **Shape and effects:** radii, control sizes, border width, depth and noise, in
  `settings["shape"]`, for both modes.
- **Browser, focus and email colours:** `theme-color` meta tags, an always-visible
  `:focus-visible` outline (`--capy-focus`), and `theme.email_colors` in hex.
- **Showcase:** colour swatches (values, contrast, source) and shape samples.
- **New dependency:** coloraide.

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
- **Template tags and context:** `{% theme_head %}`, `{% theme_html_attrs %}`,
  `{% theme_logo %}`, `{% theme_mode_toggle %}`, and a `theme` context variable
  with the published values.
- **Branding:** site name, tagline, and a main logo upload with alt text.
- **Light and dark mode** (brought forward from 6.1): a theme's default mode
  (auto, light or dark) and whether visitors can switch. `{% theme_mode_toggle %}`
  shows Light / Dark / Auto buttons; the choice is kept in a cookie for a year.
  The server and a tiny script (with the CSP nonce) apply it with no flash.
- **Theme showcase:** `/theme/showcase/`, every component in light and dark side
  by side. `CAPY_THEME_SHOWCASE` (`staff`, `public`, `off`) and
  `CAPY_THEME_BASE_TEMPLATE`.
- **Permissions:** `publish_theme` (publish, activate), `edit_custom_css` and
  `import_theme`.
- **Dependencies:** Django 6.1, jsonschema, Pillow.
