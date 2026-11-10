# Changelog

## Unreleased

- **Custom CSS:** a CSS box on the theme (permission `edit_custom_css`), published
  with it and served as its own file after the theme stylesheet, with an on/off switch.

## 0.7.0

Portability and the API: other apps and sites can use the theme, and the
live editor shows every component and what visitors see.

- **JSON API** at `/theme/api.json`: the same data as `get_artifacts()` (now also
  with font files, shape values and type settings), public, with ETag and 304.
  In projects with Django REST Framework it's a DRF view that drf-spectacular
  documents automatically; `CAPY_THEME_API` (`auto`, `drf`, `django`) chooses.
- **Design tokens download** at `/theme/tokens.json`: the published theme in the
  W3C Design Tokens format (2025.10), validated against the official schema in tests.
- **daisyUI theme blocks** at `/theme/daisyui-theme.css`: the published theme as
  `@plugin "daisyui/theme"` blocks (light and dark) to compile into a project's own CSS.
- **Theme export and import:** **Export** on a theme's admin page downloads a zip
  (settings, images, fonts); **Import theme** brings it in as an unpublished draft,
  checked like uploads (needs `import_theme`).
- **Management commands:** `theme_export`, `theme_import` (`--publish`,
  `--activate`), `theme_publish` (`--note`, `--activate`) and `theme_rebuild_images`.
- **Developer docs page** (`docs/developers.md`): every CSS variable, the API with an
  example, and the downloads; tests keep it matching the code.
- **See it as a visitor** in the live editor: shows the published theme visitors
  get (optionally in light or dark, with an offered theme, or on a chosen date to
  check schedules), with a summary of what's set up for visitors.
- **Components view in the live editor** replaces the showcase page: **Show all
  components** opens every daisyUI component in the draft theme, light and dark,
  updating as you edit. It runs in an iframe, so its stylesheet never touches the
  page being edited.
- **Images and icons in the Components view:** every logo slot and its fallback,
  the generated icons, the sharing image and the backgrounds.
- **Removed:** the showcase page (`/theme/showcase/`) and its settings
  `CAPY_THEME_SHOWCASE` and `CAPY_THEME_BASE_TEMPLATE`. **Edit live** in the
  admin now opens the editor on the site's home page.
- **Reorganised into sections** (no behaviour change): `themes/`, `colors/`,
  `css/`, `fonts/`, `images/`, `editor/`, `artifacts/`, `admin/` and `showcase/`,
  each made of small files (every Python file under 200 lines). daisyUI's
  built-in themes are now a JSON data file. Import paths inside the package
  changed; `capy_theme.artifacts.get_artifacts`, `capy_theme.models`, the template
  tags, URLs and the context processor are unchanged. The README is shorter, with
  one page per section in `docs/`.
- **Data moved out of Python into JSON files**, next to the code that reads them:
  system font stacks, character sets, shape and type settings, image slots,
  the SVG allow-list, icon files and colour groups. Same values (checked one by
  one); no behaviour change.

## 0.6.0

Visitors and scheduling, and a clearer scope: capy-theme owns the theme and
makes its artifacts available; other modules apply them.

- **Scope: capy-theme exposes theme artifacts, other modules apply them.**
  `capy_theme.artifacts.get_artifacts()` and `{% theme_artifacts %}` give every
  published colour (OKLCH and hex), font, logo slot (with fallbacks and smaller
  copies), icon, sharing image and background as plain data, with absolute URLs
  when given a request.
- **Visitor theme picker:** tick **Offer to visitors** on published themes;
  `{% theme_picker %}` lets visitors choose one (stored in a cookie, only offered
  themes count). `CAPY_THEME_VISITOR_THEMES` turns it off. Migration 0012.
- **Scheduling:** a **Theme schedule** in the admin: themes that are live between
  two dates and win over the default while running; the default returns
  afterwards. The cache expires at the next start or end. Migration 0013.
- **Device accessibility settings:** the theme stylesheet reduces every animation
  and transition when visitors ask for reduced motion, and removes noise and depth
  and thickens borders and focus outlines when they ask for more contrast.
- **Showcase: mode and visitors:** the default mode and the mode toggle, the
  visitor theme picker, and scheduled themes with their dates.
- **Removed** (added in 0.5.0, out of scope): the web app manifest view and its
  link, the Web app settings, the Open Graph/Twitter tags in `{% theme_head %}`,
  `{% theme_social_tags %}` and the sharing description. Migration
  `0011_remove_app_and_social_settings` removes their settings. The icons and the
  sharing image stay, as artifacts.

## 0.5.0

Images and icons: logos, icons, link previews and backgrounds, all made from
uploads and chosen in the live editor or the admin.

- **Safe image uploads:** `ThemeAsset` and `ThemeAssetVariant` models, ten image
  slots with size limits. Files are checked by content (PNG, JPEG, WebP, GIF, SVG)
  and saved again without EXIF, so GPS locations and camera details are removed.
- **SVG cleaning:** a strict allow-list keeps only drawing elements; scripts,
  event handlers, embedded HTML and external references are removed. The email
  logo, icon and sharing image take PNG or JPEG instead of SVG (nothing is
  converted).
- **Logo slots:** main, stacked, mark, wordmark, email and print, each with an
  optional dark version and fallbacks. `{% theme_logo slot="…" %}` outputs a
  `<picture>` with AVIF, WebP and PNG/JPEG copies, `srcset`/`sizes` from the header
  heights (40 px, 32 px on phones), and light/dark switching. **The old single
  logo field is replaced:** migration `0010_logo_slots` moves it into the main slot.
- **Icons and favicons:** from one square icon, on publish: `favicon.ico`,
  `favicon.svg` (with a dark version), the Apple icon, 192/512 px, maskable and
  monochrome icons, with background and padding settings. Linked by
  `{% theme_head %}`.
- **Web app manifest** at `/theme/manifest.webmanifest`: names, description, start
  URL, display, orientation, colours and icons. Chrome reports it installable.
- **Link previews:** a sharing image cropped to 1200 × 630 and Open Graph / Twitter
  card tags in `{% theme_head %}`, overridable per page with
  `{% theme_social_tags %}` in a block.
- **Background images:** an optional login background and page pattern, as CSS
  variables, helper classes and template values.
- **Showcase:** every logo slot and fallback, every icon at its real size, a mock
  link preview, the backgrounds and the manifest.
- **No new dependencies:** Pillow does the image work, including AVIF.

## 0.4.0

Fonts: fonts for every role from every source, all self-hosted (except external
stylesheets), chosen in the live editor.

- **Font library and roles:** `Font` and `FontFile` models. Body, heading,
  monospace and display roles in theme settings, in the admin and the live editor.
  `@font-face` rules (`font-display: swap`) and variables (`--font-sans`,
  `--font-mono`, `--capy-font-heading`, `--capy-font-display`). Published fonts are
  copied into revisions.
- **System font stacks:** 13 stacks (System sans/serif/mono plus ten from Modern
  Font Stacks), added by migration. Nothing to download.
- **Curated collection:** 30 open-licence (OFL) fonts bundled, added with
  `manage.py capy_theme_add_fonts`, with previews in the admin and editor.
- **Uploads:** WOFF2, WOFF, TTF or OTF, checked and converted to WOFF2 with
  fontTools, optionally trimmed to a character subset. Weight and style are read
  from the font. Size limit `CAPY_THEME_FONT_MAX_BYTES`.
- **Google Fonts import:** downloaded once and served from your own site.
- **External font stylesheets** (e.g. Adobe Fonts), with CSP guidance.
- **Type scale:** base size (minimum 14 px), heading scale, line height and heading
  weight. Preload links for the body and heading fonts.
- **Showcase:** fonts and type, showing only weights that really exist.
- **Fixes:** every weight gets its own `@font-face` even when files are shared;
  theme base rules beat Tailwind's reset whatever the loading order.
- **New dependency:** fonttools[woff] (with Brotli).

## 0.3.0

The live theme editor: edit a theme on the real page and see every change
instantly, then save the draft or publish it.

- **Editor on the showcase and on any page:** staff who can change themes get an
  **Edit theme** button (on the showcase, and in the corner of every page via
  `{% theme_head %}`; `CAPY_THEME_EDITOR_BUTTON` hides the corner one) and
  `?edit=<id>`. The draft shows for that user only, with a banner and Exit.
- **Controls:** base themes; the 20 colours for light and dark (picker, any
  format, reset, live contrast badge); shape and effects.
- **Palette suggestions:** analogous, complementary and triadic from the primary
  colour, and the logo's main colours.
- **Preview endpoint:** the server works out text colours, shades, contrast and
  CSS with the same code as publishing, and never writes.
- **Save draft and Publish** from the editor (Publish needs `publish_theme`), with
  an unsaved-changes warning.
- **History:** a Revisions page per theme to compare any two revisions and
  restore an old one as a new revision.
- **Admin:** sections reordered, advanced parts folded, and an **Edit live** link.
- Plain JavaScript and CSS (no framework), CSP-safe.

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
