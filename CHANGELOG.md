# Changelog

## 1.0.0 (2026-11-16)

The first stable version. Custom CSS, multiple sites (a theme per domain),
project settings, uploading images where they're used, saving, publishing and
activating in one place, and a full round of security hardening from the
pre-release reviews and the final audit.

- **Final security audit fixes** (#275): the theme Revisions, Restore and Export admin pages answer a malformed id (such as `abc`) with "not found" instead of a server error, and the editor's draft custom CSS is only served to editors (active staff who can edit themes and custom CSS), like every other editor address.
- **Save, publish and activate in one place** (#273). At the bottom of a theme's
  admin page, **Save and publish** shows where the theme stands (unpublished
  changes, published revision, whether it's the default theme, and what a running
  schedule shows instead) and has **Save
  draft**, **Save and publish** and **Save, publish and activate**, each with a
  line saying what it does, plus an optional note for the history. Save draft stays
  on the page; Django's "Save and add another" and "Save and continue editing" are
  gone, and so are the top-right Publish button and the separate publish page. The
  theme list has **Publish**, **Publish and activate** and **Activate** buttons on
  each row instead of the Activate action in the dropdown; publishing and
  activating ask first. The live editor has the same three buttons. The list's
  "Active" column is now "Showing now". For code: `publishing.publish_and_activate()`
  and `active.default_theme()`.
- **Images are uploaded and chosen where they're used** (#271), in the admin
  (Branding: Logos, More logo versions, Icon, Backgrounds, Sharing image) and the
  live editor (sections of the same names). The separate Images tab and the
  editor's upload form and "Where images are used" box are gone. Each slot says
  what it's for, its limits and what happens when it's empty; shows its current
  image and a choice of earlier uploads; and takes a new upload, which is chosen
  straight away. Most sites only need the main logo, so the other five logo
  versions are folded under "More logo versions (optional)". Email and print logos
  no longer offer a dark image (they always used the light one).
- **Alt text can be edited after upload** (admin and live editor). In the admin,
  the alt text box belongs to the image saved for the slot (named by its file) and
  only ever changes that image, and a new upload has its own alt text box. Changing
  one image's alt text differently in two places in one save is refused with a
  message, never silently dropped.
- **Media** (admin) lists every uploaded image with where it's used. An image
  nobody uses can be deleted. One the draft uses can be deleted once another image
  is chosen; one that has been published can't be (restoring a published version
  needs its images), and the message says so. Managing images now needs the
  change-theme permission (as uploading did), not the image model's own
  permissions.
- **The live editor shows the draft's logos and tab icon** on the page before
  publishing (only in your browser), and previews the icon's background and
  padding. For staff who can edit themes, `{% theme_logo %}` marks each logo with
  `data-capy-logo-slot` so the editor can find it; visitors get the same HTML.
- **The live edit page header shows the theme being edited** (its draft logo,
  site name and tagline), not the published site theme.
- **The editor's Upload button can't send twice** (#222), and a dark image can't be
  uploaded for a slot that only has a light one. Save draft drops such a choice
  left in older themes, as the admin does.
- **Live edit page: Switch theme** replaces the visitors' theme picker in the
  header. It lists every theme (unpublished ones marked) and opens the editor on
  the one you pick, asking first if there are unsaved changes. Before, the menu
  changed your visitor theme: the page flashed that theme's colors, then went
  back to the draft being edited while the logo stayed changed (#269).
- **Every fold starts closed,** in the live editor and on the theme admin page,
  including Basic colors. Click a title to open it. In the editor, folds stay as
  you left them after Save draft, Publish or Revert, as before. In the admin, a
  section with errors is shown unfolded (Django does this), and on the Add page
  focus goes to the first field with an error, or else the first section's title
  (#267).
- **Every section of the live editor can be folded** (click its title), like the
  admin page; Save and publish stays open. Every fold, including the ones inside
  Colors, stays as you left it after Save draft, Publish or Revert (#265).
- **Live editor: Revert, and no more "See it as a visitor":** a **Revert** button
  next to Save draft throws away the unsaved changes and goes back to the saved
  draft (it asks first). "See it as a visitor" and its `/theme/editor/visitor-view/`
  endpoint are removed: the page shows the draft as you edit, which is what
  visitors get once it's published (#261).
- **Every section of the theme admin page can be folded,** including the image and
  revision lists. The first section is now titled "Name".
- **Docs:** Python 3.14+ and `USE_TZ = True` are required; SQLite and PostgreSQL
  are the supported databases; run `collectstatic` on install and after updates;
  fonts on another media origin need `Access-Control-Allow-Origin`; the
  permissions table is up to date; `export_theme`/`import_theme` called from code
  need the user's permissions passed in; after upgrading to 1.0, re-run
  `theme_rebuild_images` and publish each theme again, and rename any theme
  whose slug is `default` (#255).
- **Images uploaded in the admin get their copies:** header logos uploaded in the
  theme page's Images list now get their smaller copies, and sharing images their
  1200 × 630 copy, as editor uploads already did. Before, link previews had no
  image (#254).
- **The slug `default` is reserved:** visitors could never choose a theme with it,
  since `/theme/choose/default/` means the site's own theme. An imported theme
  with that slug gets `default-imported` (#254).
- **A failed Google font file download** says "Google Fonts couldn't be reached"
  instead of giving a server error (#254).
- **Animated header logos keep moving:** they get no resized copies (those kept
  only the first frame), so the original is used (#254).
- **Published fonts follow `MEDIA_URL`:** revisions now store each font file's
  name and build its URL when the CSS is made, as images do, so a new media
  address or CDN applies to published themes too. Revisions published before
  keep their stored URLs. Themes using uploaded or Google fonts show "Unpublished
  changes" until they're published again (#254).
- **A theme's name can't add CSS to pages:** a name containing `*/` ended the
  comment it's written into at the top of the theme stylesheet (and the editor's
  preview and the daisyUI download), so anyone who could rename a theme could add
  CSS to every page. It's now kept inside the comment (#253).
- **Admin image uploads are refused on their size before being read** (#253).
- **The mode and theme-choice cookies are `Secure` on HTTPS** (#253).
- **Theme imports can't unpack more than they say:** a zip entry that claimed a
  few bytes was unpacked in full before being refused, so a tiny crafted import
  could use hundreds of MB. Each file is now read up to its stated size only, and
  entries packed with anything but deflate (or stored) are refused as damaged (#251).
- **A font with a damaged layout table gets "isn't a font"** instead of a server
  error (#251).
- **Escape in the Components view closes only that view,** not the whole editor,
  as before #245 (#251).
- **Live editor keyboard focus:** opening the editor moves focus into its panel,
  and closing it (with its buttons or Escape) puts focus back on what opened it.
  After Save draft or Publish, focus stays on that button instead of being lost.
  On narrow screens and at high zoom, where the panel covers the page, the page
  behind it can't be reached with Tab (#245).
- **Works under a strict Content Security Policy in more places:** the Components
  view's sample form no longer uses an inline `onsubmit` (it's no longer a form,
  so Enter can't reload the page), its radial progress gets its value from the
  bundled stylesheet instead of a `style` attribute, and the admin's color pickers
  are sized by `color_input.js` instead of a `style` attribute (#244). The rest
  of #214 is still open.
- **A failed restore keeps the draft:** restoring an old revision saved it over the
  theme's draft before publishing it, so if publishing failed (for example,
  restoring the revision that's already live), unpublished edits were lost. Now
  the draft is only changed if the restore succeeds (#243).
- **Font files can't unpack into huge amounts of memory:** WOFF and WOFF2 fonts are
  compressed, and a crafted file of under 1 KB could unpack to 512 MB. Before a
  font is opened, capy-theme now checks the sizes it says it unpacks to and refuses
  anything over the new `CAPY_THEME_FONT_MAX_UNPACKED_BYTES` setting (30 MB). It
  then unpacks it in small steps and refuses it as soon as it gives more than it
  said. This covers admin uploads, theme imports and Google Fonts downloads. WOFF2
  font collections are refused.
- **Fonts are read in their own process, with memory and time limits:** a small
  font can still be costly to read (a 5 KB font of densely packed glyphs took 57 s
  and almost 1 GB). fontTools now runs in a separate process limited by
  `CAPY_THEME_FONT_MAX_MEMORY_BYTES` (512 MB) and `CAPY_THEME_FONT_MAX_SECONDS`
  (30); a font over either is refused as too complex. A damaged font now always
  gets "isn't a font", never a server error, whichever step it breaks.
- **Safer minimum versions:** fontTools must be 4.60.2 or newer (older versions
  have known security problems), and brotli, which unpacks WOFF2 fonts, is now a
  direct dependency at 1.2.1 or newer (brotlicffi 1.2.1.0 or newer on PyPy; older
  versions have known memory-safety bugs). Pillow no longer has an upper version
  cap, so projects can take its security fixes, which only go into its newest
  major version.
- **Font names and font fields can't inject script or CSS:** a font's family name
  (letters, digits, spaces and hyphens), fallback fonts (a comma-separated list of
  names) and character ranges (`U+…` values) are now checked, in the admin and in
  theme imports (migration 0016). Before, they went into the admin's font previews
  and every page's stylesheet as they were, so a crafted name could run script in
  the admin, and a fallback list could add any CSS to public pages. The admin's
  previews also escape every value, and so does the page CSS, which also drops any
  saved value that doesn't pass the checks (fonts saved before this release aren't
  re-checked otherwise). Importing a theme that adds an external font now needs
  permission to add fonts.
- **Uploaded SVGs can't load outside files through CSS tricks:** CSS escapes
  (`\75rl(`), `image-set()` and `@font-face` are now removed like `url()` is, and
  a `<style>` keeps only its text, checked as a whole. The
  README recommends `nosniff` and a strict CSP header for uploaded files.
- **Limits on imports, font downloads and big images:** a theme import that uses
  the same file more than once is refused, as is a zip over the size limit (now
  checked on the upload itself too) or with more than `CAPY_THEME_IMPORT_MAX_FILES`
  (200) files. A damaged zip gives "The export is damaged." instead of a server
  error. Font uploads in the admin are refused on their size before being read.
  Google Fonts downloads follow redirects only to Google Fonts addresses and are
  read up to the font size limit. A Google import that fails partway leaves no
  files behind. Still images are refused before decoding if they have more than
  `CAPY_THEME_IMAGE_MAX_PIXELS` (25 million) pixels.
- **Custom CSS stays with those allowed to see it:** Export leaves out a theme's
  custom CSS for users without the edit_custom_css permission. Restoring a revision
  without that permission keeps the draft's current custom CSS instead of bringing
  back the old one. "Offer to visitors" can only be changed by users who can
  publish, since it puts a theme in front of visitors.
- **Faster, safer custom CSS reading:** the Components view finds custom CSS
  selectors in linear time. Crafted CSS (many unclosed comments, or long text with
  no `{`) could tie up a worker for seconds.
- **`Vary: Cookie` on the theme API and downloads:** `/theme/api.json`,
  `tokens.json` and `daisyui-theme.css` depend on the visitor's theme choice.
  Shared caches (CDNs, proxies) now keep one copy per cookie instead of serving one
  visitor's choice to everyone.
- **Colors and numbers that broke every page are refused:** a color such as
  `oklch(50% 1e300 0)` passed validation, then every page using the theme returned
  an error once it was published. Colors are now refused unless they're real colors
  (lightness 0–100%, chroma up to 0.5), and NaN or infinite numbers are refused
  anywhere in a theme's settings, in the admin, the editor and imports. A negative
  hue (e.g. -30) is now saved as the same color (330) instead of failing.
- **Tabs on the theme edit page in the admin:** its sections are grouped into tabs
  (General, Branding, Fonts, Light colors, Dark colors, Shape and contrast, Images,
  Revisions, Advanced) instead of one long scroll. Inside a tab every section is open,
  except the colors' Advanced and Expert groups. After a failed save, the first tab
  with an error opens and tabs with errors are marked. Keyboard and screen-reader
  friendly. Presentation only: the fields, saving and permissions are unchanged, and
  without JavaScript the page reads top to bottom as before.
- **Live edit page at `/theme/live-edit/`:** capy-theme's own page for building a
  theme. It has the header (logo, site name, tagline, Light / Dark / Auto, theme
  picker) and every daisyUI component, with the live editor open on it. It's
  self-contained (its own template and bundled stylesheet), so it's the same in
  every project, and it's for staff who can edit themes. The admin's **Edit live**
  now opens it instead of the site's home page.
- **New dependency `defusedxml`:** uploaded SVGs are parsed with it, as a second
  layer against entity ("XML bomb") attacks on top of the existing DOCTYPE check.
- **CSP nonces work with Django's real CSP middleware:** the light/dark script
  now always gets the request's nonce. Before, a page where nothing else had used
  the nonce sent none, so browsers blocked the script under `script-src` with `NONCE`.
- **Animated GIF uploads keep how each frame is cleared:** GIFs whose frames
  "clear to the background" no longer show earlier frames after cleaning. (A GIF
  that mixes clearing settings between frames can still differ: a Pillow limitation.)
- **American spelling everywhere** (color, license, catalog, gray, center...), in
  the interface, docs and code. `Font.licence` is now `Font.license` (migration
  0015 renames it, keeping every value), and the modules `themes/catalogue.py`
  and `colors/maths.py` are now `themes/catalog.py` and `colors/color_math.py`.
  Theme exports made before 1.0 (with `"licence"`) still import.
- **Mode toggle:** the current mode is marked with `aria-current="true"` instead
  of `aria-pressed`, which isn't allowed on links (found by Lighthouse). Project
  CSS or tests that look for `[aria-pressed]` on the toggle need updating.
- **Components view, final pass:** every editor setting shows there (unsaved image
  choices, an icon preview with the draft's background and padding, all heading
  levels and the display font), plus which domain's theme it shows and the custom
  CSS (with the selectors it styles). Accessibility fixes for its samples.
- **Project settings:** all in `capy_theme/conf.py`, each tested and listed in the
  README. New: `CAPY_THEME_CUSTOM_CSS`, `CAPY_THEME_IMAGE_MAX_BYTES`,
  `CAPY_THEME_IMPORT_MAX_BYTES` and the three `CAPY_THEME_ANIMATION_*` limits
  (the font, image-pixel and import-file limits are described above).
- **Multiple sites:** **Site themes** in the admin give a domain its own theme;
  schedules can be limited to one domain. Everything follows the request's domain
  (migration 0014).
- **Custom CSS:** a CSS box on the theme (permission `edit_custom_css`), published
  with it and served as its own file after the theme stylesheet, with an on/off switch.
- **Limits on animated images:** an uploaded animated image (GIF, WebP or PNG) is refused if it
  has more frames, is wider or higher, or has more pixels in all than
  `CAPY_THEME_ANIMATION_MAX_FRAMES` (500), `CAPY_THEME_ANIMATION_MAX_SIZE` (2000)
  and `CAPY_THEME_ANIMATION_MAX_PIXELS` (50 million) allow, and GIFs whose frames
  reach past the image's edges are refused (#188).
- **Metadata is stripped from every frame of animated GIFs,** not just the first
  (#185).
- **Logging:** important events (publishing, restoring, activating, importing,
  Google font imports, Google Fonts unreachable) go through loggers under
  `capy_theme`; the project's `LOGGING` decides where they go. See the README's
  Logging section (#208).
- **MIT license:** `LICENSE` and `THIRD_PARTY_NOTICES.md` (for the bundled
  daisyUI, Tailwind and fonts) ship with the package (#203).
- **The open editor makes room for the page** instead of covering it, on screens
  48rem and wider (#193).
- **The editor's file chooser** is styled like its other buttons (#221).
- **Shape size fields in the admin step by 0.0625,** so every arrow stop is a
  value that saves (#224).
- **An empty custom CSS isn't stored** (#176).
- **Tighter redirect, cookie and frame checks:** the "next" address after
  choosing a mode or theme must be on this site; the mode and theme-choice
  cookies store only allowed values; the Components view only loads a page on
  this site's origin (#195).
- **Docs:** a Backing up section in the README (#210) and a note on running the
  app server with a worker timeout and memory limit in production.

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
- **Reorganized into sections** (no behavior change): `themes/`, `colors/`,
  `css/`, `fonts/`, `images/`, `editor/`, `artifacts/`, `admin/` and `showcase/`,
  each made of small files (every Python file under 200 lines). daisyUI's
  built-in themes are now a JSON data file. Import paths inside the package
  changed; `capy_theme.artifacts.get_artifacts`, `capy_theme.models`, the template
  tags, URLs and the context processor are unchanged. The README is shorter, with
  one page per section in `docs/`.
- **Data moved out of Python into JSON files**, next to the code that reads them:
  system font stacks, character sets, shape and type settings, image slots,
  the SVG allow-list, icon files and color groups. Same values (checked one by
  one); no behavior change.

## 0.6.0

Visitors and scheduling, and a clearer scope: capy-theme owns the theme and
makes its artifacts available; other modules apply them.

- **Scope: capy-theme exposes theme artifacts, other modules apply them.**
  `capy_theme.artifacts.get_artifacts()` and `{% theme_artifacts %}` give every
  published color (OKLCH and hex), font, logo slot (with fallbacks and smaller
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
  URL, display, orientation, colors and icons. Chrome reports it installable.
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
- **Curated collection:** 30 open-license (OFL) fonts bundled, added with
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
- **Controls:** base themes; the 20 colors for light and dark (picker, any
  format, reset, live contrast badge); shape and effects.
- **Palette suggestions:** analogous, complementary and triadic from the primary
  color, and the logo's main colors.
- **Preview endpoint:** the server works out text colors, shades, contrast and
  CSS with the same code as publishing, and never writes.
- **Save draft and Publish** from the editor (Publish needs `publish_theme`), with
  an unsaved-changes warning.
- **History:** a Revisions page per theme to compare any two revisions and
  restore an old one as a new revision.
- **Admin:** sections reordered, advanced parts folded, and an **Edit live** link.
- Plain JavaScript and CSS (no framework), CSP-safe.

## 0.2.0

Colors and shape: every color and shape value can be overridden, with readable
text guaranteed.

- **Color overrides:** any of the 20 daisyUI colors, separately for light and
  dark, in `settings["colors"]`. Admin fields grouped Basic / Advanced / Expert;
  blank fields use (and show) the base theme's color.
- **Color input:** hex, rgb(), hsl(), oklch() or color names, stored as OKLCH
  (ColorAide), with the browser's color picker beside each field.
- **Automatic text colors and background shades:** readable `-content` colors
  for overridden colors (WCAG AA, white/black fallback), and base-200, base-300
  and base-content from an overridden background.
- **Contrast warnings:** WCAG ratings (fail, AA, AAA) for every color pair, next
  to each color field and in a table. Warnings only.
- **Shape and effects:** radii, control sizes, border width, depth and noise, in
  `settings["shape"]`, for both modes.
- **Browser, focus and email colors:** `theme-color` meta tags, an always-visible
  `:focus-visible` outline (`--capy-focus`), and `theme.email_colors` in hex.
- **Showcase:** color swatches (values, contrast, source) and shape samples.
- **New dependency:** coloraide.

## 0.1.0

The foundation: themes exist, one is live, and every page uses it. Publishing,
history and permissions work.

- **Built-in theme catalog:** daisyUI 5.7.50's 35 themes and their 28 values,
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
