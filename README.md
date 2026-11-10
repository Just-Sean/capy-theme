# Capy Theme

Theming for Django projects.

A self-contained Django app (`capy_theme`) that any Django 6.1+ project
can install. It has no project of its own: its tests run against a tiny
stand-in project in `tests/`, and `demo/` is a small site for trying it out.

## What it does (v0.6)

Whoever runs the site controls its look from the Django admin, with no code
changes or redeploys. The project needs a Tailwind CSS 4 / daisyUI 5 stylesheet.

- **Live theme editor:** staff edit a theme right on the page (the showcase or any
  page using `{% theme_head %}`), with colour pickers, shape controls, contrast
  ratings and palette suggestions (from the primary colour or the logo). Every
  change shows instantly, for that user only, until they **Save draft** or
  **Publish**. The admin form stays as a plain fallback.
- **Themes** are based on any of daisyUI's 35 built-in themes: one light base and
  one dark base. A project can limit which are offered.
- **Colours:** override any of the 20 colours, separately for light and dark, in
  any format (hex, rgb, hsl, oklch). Readable text colours and background shades
  are worked out automatically, and every colour pair shows its WCAG contrast
  rating.
- **Fonts:** a shared font library with body, heading, monospace and display
  roles. Fonts come from 13 system font stacks (nothing to download), 30 bundled
  open-licence fonts, uploads (any WOFF2/WOFF/TTF/OTF, converted to WOFF2 and
  trimmed to a character set), Google Fonts (downloaded once and served from your
  own site), or external stylesheets like Adobe Fonts. Plus a type scale (base
  size, heading scale, line height, heading weight) and font preloading.
- **Shape and effects:** corner radii, control sizes, border width, depth and noise.
- **Branding and images:** a site name and tagline, and uploaded images (checked
  by content, GPS and camera details removed, SVGs cleaned of scripts):
  - six logo slots (main, stacked, mark, wordmark, email, print) with dark
    versions and fallbacks, served as responsive AVIF/WebP/PNG at the header height;
  - every favicon and app icon made from one square icon;
  - a 1200 × 630 sharing image for link previews;
  - optional login and page background images.
- **Theme artifacts for other modules:** `get_artifacts()` (and
  `{% theme_artifacts %}`) give every colour, font, logo, icon and image as plain
  data, so an email module, app shell or PWA module can use the theme. capy-theme
  doesn't apply them outside the page's own look.
- **Drafts and publishing:** editing a theme changes only its draft. Publishing
  saves a numbered revision, recording who published it and when, and the site
  shows that. Every revision is kept; any two can be compared, and an old one
  restored (as a new revision).
- **One active theme:** pick it with the admin's Activate action. It's cached, so
  pages don't query the database for it.
- **On every page:** `{% theme_head %}` links the theme's stylesheet (with the
  browser address-bar colour and a visible focus outline), `{% theme_logo %}`
  shows the logo or site name, and every template gets a `theme` variable
  (including hex colours for HTML emails).
- **Light and dark mode:** follow the device or force one, and visitors can switch
  with `{% theme_mode_toggle %}`, with no flash on page load.
- **Visitors and scheduling:** visitors can pick among themes the operator offers
  (`{% theme_picker %}`); themes can be scheduled between two dates (e.g. a
  holiday theme) and the default returns afterwards; visitors' "reduce motion"
  and "more contrast" device settings are respected.
- **Theme showcase** at `/theme/showcase/`: every daisyUI component, colour swatch
  and shape setting in the active theme, with light and dark side by side (staff
  only by default).
- **Permissions:** only users with `publish_theme` can publish or activate.

Next: portability and the JSON API (v0.7), then custom CSS, multiple sites and
1.0 (see `docs/PLAN.md`).

## Add it to a project

1. Install it, from a folder next to your project or from GitHub:

   ```bash
   uv add --editable ../capy-theme                     # while developing it
   uv add git+https://github.com/Just-Sean/capy-theme --tag v0.1.0   # a pinned release
   ```

2. Add it to the project's `INSTALLED_APPS` in `config/settings.py`:

   ```python
   INSTALLED_APPS = [
       ...,
       "capy_theme",
   ]
   ```

3. Add its URLs to the project's `urls.py`, under `/theme/`:

   ```python
   from django.urls import include, path

   urlpatterns = [
       ...,
       path("theme/", include("capy_theme.urls")),
   ]
   ```

4. Add its context processor to `TEMPLATES` in `settings.py`, so every template
   gets a `theme` variable:

   ```python
   TEMPLATES = [
       {
           ...,
           "OPTIONS": {
               "context_processors": [
                   ...,
                   "capy_theme.context_processors.theme",
               ],
           },
       },
   ]
   ```

5. Add the template tags to the project's base template. `{% theme_head %}` links
   the active theme's stylesheet and adds a tiny script that applies light or dark
   mode before the page draws. `{% theme_html_attrs %}` puts the forced mode
   (`data-theme="capy-light"` or `"capy-dark"`) on `<html>`. `{% theme_mode_toggle %}`
   shows Light / Dark / Auto buttons for visitors, wherever you put it.

   ```html
   {% load capy_theme %}<!doctype html>
   <html lang="en" {% theme_html_attrs %}>
   <head>
     ...
     <link rel="stylesheet" href="...">   <!-- the project's Tailwind/daisyUI CSS -->
     {% theme_head %}
   </head>
   <body>
     <nav>... {% theme_logo %} ... {% theme_mode_toggle %} ...</nav>
   ```

   The toggle uses daisyUI's `join` and `btn` classes. Tailwind only includes
   classes it finds in scanned files, so add the module's templates to the
   project's Tailwind source with an `@source` line pointing at the installed
   `capy_theme/templates` folder.

6. Make sure the project stores and serves uploaded files, for theme logos.
   Set `MEDIA_ROOT` and `MEDIA_URL` in `settings.py`. While developing, serve them
   from `urls.py`; in production, serve that folder from the web server or a
   storage service:

   ```python
   from django.conf import settings
   from django.conf.urls.static import static

   urlpatterns = [
       ...,
       *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),  # DEBUG only
   ]
   ```

7. Create its database tables:

   ```bash
   uv run python manage.py migrate
   ```

To show the theme's logo (or its site name if it has no logo), use
`{% theme_logo %}`, or `{% theme_logo slot="mark" %}` for another logo slot (see
[Logos](#logos)). Extra attributes go on the `<img>`, e.g.
`{% theme_logo class="me-2" %}`. Every template also gets a `theme` variable
holding the published `site_name`, `tagline`, `logo_url`, `logo_alt`, `name`,
`slug`, `revision`, `light_base`, `dark_base`, `stylesheet_url`, `default_mode`,
`visitors_can_switch`, `mode` (what this visitor sees), `email_colors` (hex),
`background_login_url` and `background_pattern_url`, or `None`
if no theme is active.

Pages then show the **active** theme's **published** colours. Until a theme is
published and activated in the admin, they show daisyUI's defaults.

The module's tables go into whatever database the project uses.

## Settings

Optional settings a project can add to its `settings.py`:

| Setting | Default | What it does |
| --- | --- | --- |
| `CAPY_THEME_BUILTIN_THEMES` | all 35 | Which built-in daisyUI themes can be used as a theme's light or dark base, e.g. `["light", "dark"]`. Listing an unknown theme raises an error that names it. |
| `CAPY_THEME_CACHE_SECONDS` | `300` | How long the active theme is cached, in seconds. Publishing or activating clears the cache straight away; this limit makes every server process catch up when the project's cache isn't shared between processes (e.g. Django's default in-memory cache). |
| `CAPY_THEME_SHOWCASE` | `"staff"` | Who can see the theme showcase at `/theme/showcase/`: `"staff"` (logged-in staff; others are sent to the admin login), `"public"` (anyone) or `"off"` (nobody: 404). |
| `CAPY_THEME_BASE_TEMPLATE` | not set | A project template for the showcase to extend, e.g. `"base.html"`. It needs a `content` block (and a `title` block for the page title) and should include `{% theme_head %}`. Not set: the showcase uses its own standalone page. |
| `CAPY_THEME_VISITOR_THEMES` | `True` | Let visitors choose among the themes offered to them with `{% theme_picker %}`. `False` turns the picker off and ignores visitors' choices. |
| `CAPY_THEME_EDITOR_BUTTON` | `True` | Show the live editor's **Edit theme** button in the corner of every page, for staff who can edit. `False` hides it (the editor still opens from the showcase or with `?edit=<theme id>`). |
| `CAPY_THEME_FONT_MAX_BYTES` | `5242880` (5 MB) | The largest font file that can be uploaded, in bytes. |

## Develop it

```bash
uv sync                    # installs Python, Django and the test tools
uv run pytest              # runs the tests on SQLite, no setup needed
uv run ruff check .        # finds problems
uv run ruff format .       # formats the code
```

To run the tests on Postgres instead (needed before each release):

```bash
DATABASE_URL=postgres://app:app@localhost:5432/module_tests uv run pytest
```

If you don't have Postgres running, use a throwaway Docker container. It's
removed when stopped, and keeps no data:

```bash
docker run -d --rm --name capy-theme-pg-test -e POSTGRES_USER=app -e POSTGRES_PASSWORD=app \
  -e POSTGRES_DB=module_tests -p 127.0.0.1:55432:5432 postgres:17
docker exec capy-theme-pg-test pg_isready -U app        # repeat until it says "accepting connections"
DATABASE_URL=postgres://app:app@127.0.0.1:55432/module_tests uv run pytest
docker stop capy-theme-pg-test                            # stops and removes it
```

(`docker rmi postgres:17` deletes the downloaded image when you no longer need it.)

### Demo site

`demo/` is a tiny Django site for running and clicking through the module while
it's built. It uses the module straight from `src/` (uv installs it in editable
mode), so every change shows immediately. It is development-only and not part
of the installed package.

```bash
uv run python demo/manage.py migrate
uv run python demo/manage.py createsuperuser
uv run python demo/manage.py runserver      # then open http://localhost:8000/admin/
```

Stop the server with **Ctrl+C** in the terminal it's running in.

The demo's navbar links to the theme showcase (`/theme/showcase/`). The demo sets
`CAPY_THEME_BASE_TEMPLATE = "base.html"`, so the showcase appears inside the
demo's page with its navbar.

It uses SQLite (`demo/db.sqlite3`) by default. To use Postgres instead, set
`DATABASE_URL` on each command (the database must already exist):

```bash
DATABASE_URL=postgres://app:app@localhost:5432/capy_demo uv run python demo/manage.py migrate
DATABASE_URL=postgres://app:app@localhost:5432/capy_demo uv run python demo/manage.py runserver
```

To start the demo over with an empty SQLite database, delete it and set it up again:

```bash
rm demo/db.sqlite3
uv run python demo/manage.py migrate
uv run python demo/manage.py createsuperuser
```

The demo's home page (<http://localhost:8000/>) is an ordinary project-style page
of daisyUI components, for checking the theme works on pages the module doesn't
own. It's styled with Tailwind CSS v4 and daisyUI 5 through
[django-tailwind-cli](https://github.com/django-commons/django-tailwind-cli),
which downloads the Tailwind CLI on first use. To build the CSS and run the
server, rebuilding as templates change:

```bash
uv run python demo/manage.py tailwind runserver
```

Or build once with `uv run python demo/manage.py tailwind build`, then `runserver`.

The Tailwind source is `demo/tailwind/source.css`. It scans the demo's templates
and the module's own (`src/capy_theme/templates/`), and loads the daisyUI plugin
files (`daisyui.mjs`, `daisyui-theme.mjs`) kept next to it. To update them, see
[Updating daisyUI](#updating-daisyui).

### Updating daisyUI

The module, the demo and the showcase all use daisyUI 5.7.50. Keep them on the same version:

1. **The module's theme catalogue.** `src/capy_theme/builtin_themes.py` lists
   daisyUI's built-in themes and their values. Don't edit it by hand: it's
   generated by `scripts/generate_builtin_themes.py`, which downloads the daisyUI
   package from npm. Change `DAISYUI_VERSION` at the top of the script, then run:

   ```bash
   uv run python scripts/generate_builtin_themes.py
   ```

2. **The demo's plugin files.** Replace `demo/tailwind/daisyui.mjs` and
   `daisyui-theme.mjs` with the same version from the
   [daisyUI releases](https://github.com/saadeghi/daisyui/releases)
   (e.g. `gh release download v5.7.50 --repo saadeghi/daisyui -p daisyui.mjs -p daisyui-theme.mjs`).

3. **The showcase's bundled stylesheet.** After replacing the demo's plugin files, rebuild it:

   ```bash
   uv run python scripts/build_showcase_css.py
   ```

The script warns if the demo's `daisyui.mjs` is a different version from the
catalogue. Published themes keep the values they were published with, and the
admin flags any whose base daisyUI has changed or removed. Run the tests
afterwards. They check that every theme still has all 28 values.

To create migrations after changing models, run Django's command against the
test project:

```bash
uv run django-admin makemigrations capy_theme --settings=tests.settings --pythonpath=.
```

### Theme settings schema

Everything a theme overrides is stored in its `settings` field, a JSON object.
It's checked against `src/capy_theme/settings.schema.json` (a standard
[JSON Schema](https://json-schema.org/), validated with the `jsonschema` package)
every time a theme is saved, so data that doesn't match can't be saved. Keys the
schema doesn't list are rejected. It starts with no keys, and each phase adds its own.

When a change adds a new setting, add it to `settings.schema.json` in the same
change, with a test. No migration is needed, because `settings` is a single JSON column.

After pulling changes that add migrations, apply them to the demo database:

```bash
uv run python demo/manage.py migrate
```

### The theme's admin page

The admin page is the plain fallback to the live editor. Its sections, top to
bottom:

1. Name and slug
2. Publishing status
3. Base themes
4. Branding
5. Colours (light and dark; Basic open, Advanced and Expert folded)
6. Contrast (folded)
7. Shape and effects (folded)
8. Mode
9. Advanced (folded: stored settings, ID and dates)

At the top right: **Edit live** opens the theme in the live editor (on the
showcase, or the home page if the showcase is off), next to **Revisions**,
**Publish** and Django's **History**.

### Branding

On a theme's admin page, the **Branding** section has the site name, tagline
and logo alt text, stored in the theme's `settings`. Logos are chosen in the
**Logos** section (see [Logos](#logos)).

Like everything else, branding changes show on the site only after publishing.

### Images

A theme's images (logos, the icon, the social sharing image, backgrounds) are
uploaded in the live editor's **Images** section or in the **Images** list on
the theme's admin page. Each upload goes in a slot, for light or dark mode,
with alt text. For every upload:

- The type is worked out from the file's content, not its name. Only PNG, JPEG,
  WebP, GIF and SVG are accepted, so a text file renamed `.png` is rejected.
- Each slot has a size limit and a maximum width and height (in
  `src/capy_theme/images.py`, `SLOTS`): 1 MB for the email logo, 2 MB for the
  other logos, the icon and the background pattern, and 5 MB for the print logo,
  social image and login background.
- The image is saved again without EXIF, text chunks and comments, so camera
  details and GPS locations are removed. Photos are turned upright first.
  Colour profiles are kept.
- SVGs are cleaned with a strict allow-list (`src/capy_theme/svg.py`): only
  drawing elements and attributes are kept. Scripts, event handlers (`onload`
  and so on), embedded HTML, animation, links to other files or sites, and CSS
  `@import` or external `url()` are removed. SVGs must be UTF-8, and SVGs with a
  DOCTYPE or entities are rejected.
- SVGs aren't converted to PNG. The slots where SVG can't be used take a PNG,
  JPEG, WebP or GIF instead: the email logo (email programs don't show SVG), the
  social sharing image (social sites don't accept it) and the icon (favicons are
  made from it). They're listed in `NO_SVG` in `src/capy_theme/images.py`.

Files are stored under `MEDIA_ROOT/capy_theme/assets/<slot>/`. An image is never
changed after upload: a new image is a new asset, so older revisions keep theirs.
Uploading doesn't change what visitors see: an image is only used once it's
chosen for its slot and the theme is published.

### Logos

There are six logo slots: **main**, **stacked**, **mark**, **wordmark**,
**email** and **print**. Each can have a light and a dark image. To set one:

1. Upload the image for that slot (live editor: **Images**; admin: the
   **Images** list, then save).
2. Choose it for the slot (live editor: **Images → Logos**; admin: **Logos**).
3. Save the draft and publish.

Fallbacks: dark mode uses the slot's light image if there's no dark one, and a
slot with no image uses the main logo.

`{% theme_logo slot="main" %}` (the default) outputs the logo for that slot:

- **Header slots** (main, stacked, mark, wordmark) give a `<picture>` with AVIF
  and WebP sources and a PNG or JPEG fallback. On upload, smaller copies are made
  at widths from 64 to 1280 px (and the image's own width, up to 2560), stored
  under `MEDIA_ROOT/capy_theme/assets/<slot>/variants/`. The `sizes` attribute
  comes from the header heights, so phones download a smaller file. SVG logos
  are used as they are.
- **Header heights**: the **Header logo height** (default 40 px) and **on
  phones** (default 32 px, for windows up to 640 px wide) are set in the same
  Logos section. The theme's stylesheet sizes `img.capy-logo` with them; a
  utility class on the tag (e.g. `class="h-12"`) still wins.
- **Light and dark**: if the slot has a dark image, both are output and the
  theme's stylesheet shows the one for the current mode (it follows the toggle
  and the device setting). Both are `loading="lazy"`, so only the one shown is
  downloaded.
- **Email and print** slots give a plain `<img>` of the light image (email
  programs don't handle `<picture>` or the light/dark CSS).

Alt text comes from the image's alt text, then the theme's logo alt text, then
the site name.

### Icon and favicons

Every browser and home-screen icon is made from one square image (at least
512 × 512 px is best; SVG isn't accepted here). To set it:

1. Upload it in the **icon** slot (live editor: **Images**; admin: the
   **Images** list), optionally with a dark version.
2. Choose it (live editor: **Images → Logos and icon**; admin: **Icon**), and set
   the **Icon background** (a hex colour; blank is transparent) and **Icon
   padding** (0–25% on each side) if you want.
3. Save and publish. The icons are made when you publish.

The files are saved in `MEDIA_ROOT/capy_theme/icons/<id>/`, where the id comes
from the icon image and its settings, so each revision keeps its icons:

| File | Used for |
| --- | --- |
| `favicon.ico` | Browser tab (16, 32 and 48 px in one file) |
| `favicon.svg` | Browser tab; switches to the dark icon in dark mode |
| `apple-touch-icon.png` | iPhone and iPad home screen (180 px, never transparent: white if no background is set) |
| `icon-192.png`, `icon-512.png` | Android home screen and app icons |
| `icon-maskable-512.png` | Android adaptive icons: the icon sits in the middle 80%, on a solid background |
| `icon-monochrome-512.png` | Single-colour icons: white in the icon's shape |

`{% theme_head %}` links the ICO, SVG, 192 px and Apple icons (the tab and
home-screen icon are part of the site's look). The 512 px, maskable and
monochrome icons are for a web app manifest, which capy-theme doesn't serve: a
project or PWA module gets them from [theme artifacts](#theme-artifacts-for-other-modules).

### Sharing image

Choose an image for the **social** slot (PNG or JPEG, not SVG) in the live
editor (**Images**) or the admin (**Sharing image**), then publish. It's cropped
from its centre to 1200 × 630 when uploaded (transparent parts become white).
capy-theme doesn't output link-preview tags (Open Graph, Twitter cards): the
project or another module adds them, using the image from
[theme artifacts](#theme-artifacts-for-other-modules).

### Background images

Two optional decorative images, each with a light and dark version: a **login
background** and a **page background pattern** (SVG allowed). Choose them in
the live editor (**Images**; they preview straight away) or the admin
(**Backgrounds**), then publish. They show only where the project's templates
use them:

- **Classes**: `class="capy-bg-login"` (covers the element, centred) or
  `class="capy-bg-pattern"` (repeats). The demo's `<body>` uses `capy-bg-pattern`.
- **CSS variables**: `--capy-bg-login` and `--capy-bg-pattern` (each a `url(...)`,
  switching with light and dark mode), e.g.
  `background-image: var(--capy-bg-login);` in the project's CSS.
- **Template values**: `{{ theme.background_login_url }}` and
  `{{ theme.background_pattern_url }}` (the light versions; `""` if not set).

Dark mode uses the light image if there's no dark one.

### Theme artifacts for other modules

capy-theme owns the theme but only applies it to the page's own look (the
stylesheet, the logo tag, the tab icon). Everything else it produces is made
available for other parts of the project, e.g. an email module, an app shell,
or something that builds a web app manifest or link-preview tags:

```python
from capy_theme.artifacts import get_artifacts

artifacts = get_artifacts(request)  # None if no theme is published
artifacts["logos"]["logo_email"]["light"]["url"]  # every logo slot, light and dark
artifacts["colors_hex"]["light"]["primary"]  # also "colors" (OKLCH)
artifacts["icons"]["icon-512.png"]  # every generated icon
artifacts["sharing_image"]  # url, width, height, alt
```

In templates: `{% theme_artifacts as artifacts %}`, then e.g.
`{{ artifacts.logos.logo_email.light.url }}`.

What's in it (all from the published revision; with a request, URLs are absolute):

| Key | Contents |
| --- | --- |
| `theme` | `name`, `slug`, `revision` |
| `branding` | `site_name`, `tagline`, `logo_alt` |
| `colors`, `colors_hex` | The 20 colours per mode (`light`, `dark`), as OKLCH and as `#rrggbb` |
| `fonts` | Per role the theme sets: `family`, `stack` (CSS `font-family`), `source` |
| `logos` | The six logo slots, `light` and `dark`, after fallbacks: `url`, `width`, `height`, `alt`, `content_type`, `variants` (smaller copies: `url`, `width`, `format`) |
| `icons` | File name → URL: `favicon.ico`, `favicon.svg`, `apple-touch-icon.png`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `icon-monochrome-512.png` |
| `sharing_image` | `url`, `width`, `height`, `alt` (1200 × 630), or `None` |
| `backgrounds` | `login` and `pattern`, each `light` and `dark` URL (or `None`) |
| `mode` | `default`, `visitors_can_switch` |
| `stylesheet_url` | The theme stylesheet |

The JSON API (7.1) will serve the same data.

Upgrading from 0.5: migration `0011_remove_app_and_social_settings` removes the
web app manifest and link-preview settings from 0.5.0 (the manifest view and
the tags are gone; the icons and sharing image stay).

Upgrading from 0.4: migration `0010_logo_slots` moves each theme's old logo into
its main slot (light). It has no smaller copies; upload it again to get them.
Revisions published before 0.5 keep showing their old logo.

The "Overrides" section shows the theme's stored `settings` as read-only JSON.
They're edited through the fields above, not typed by hand.

### Colours

On a theme's admin page, the colour sections let you override any of daisyUI's
20 colours, separately for light and dark mode:

- **Basic** (shown open): primary, secondary, accent, neutral, background and
  text on background.
- **Advanced** (folded): info, success, warning, error, and the two darker
  background shades.
- **Expert** (folded): the text colour on each coloured element.

Leave a field blank to use the base theme's colour, which is shown greyed out
in the empty field. Only the colours you set are stored, in `settings["colors"]`;
the rest always come from the base. Enter colours any common way, such as `#3b82f6`, `rgb(59 130 246)`,
`hsl(217 91% 60%)`, `oklch(62% 0.19 260)` or a colour name, or use the colour
picker beside each field. They're converted to and stored as OKLCH (daisyUI's
format), so after saving the field shows e.g. `oklch(62.31% 0.188 259.81)`.
Like everything else, they show on the site after publishing.

**Readable text is worked out for you.** When you set a colour (say primary) but
not its text colour (primary text), the text colour is chosen automatically: a
very light or very dark tint of the same hue, whichever reads better, falling
back to pure white or black if a tint wouldn't meet WCAG AA (4.5:1). When you set
the background but not its darker shades or its text, those are worked out from
it as well. Anything you set yourself is always kept.

**Contrast warnings.** Each colour field shows the WCAG contrast of its pair
(e.g. *Primary / Primary text: 4.7:1, passes AA*), and the **Contrast** section
lists every pair for light and dark. AA needs 4.5:1 and AAA 7:1 for normal text.
Pairs below AA are marked "⚠ fails AA". They're warnings only: saving and
publishing still work. Ratings are for the saved draft, so save to update them.

### The live theme editor

Staff who can change themes see an **Edit theme** button: on the showcase, and in
the bottom-right corner of **every page** that uses `{% theme_head %}`. It opens
a panel on the right and shows the theme's **draft** on the page you're on, in
your browser only. Visitors keep seeing the published theme, and a banner at the
top says so. **Close** (or **Exit** in the banner) puts the page back to the
published look.

The editor is loaded by `{% theme_head %}` only for staff with the change-theme
permission; visitors get none of its files. To hide the corner button (for
example, to put your own link to `?edit=<id>` somewhere), set
`CAPY_THEME_EDITOR_BUTTON = False`.

The panel has:

- **Base themes:** the light and dark base.
- **Colours:** Light and Dark tabs, with Basic open and Advanced and Expert
  folded. Each colour has the browser's colour picker, a text box (any format),
  **Reset** (back to the base colour) and its contrast rating, e.g. "AA 5.19" or
  "⚠ fail 2.1". Overridden colours are shown in bold with a dot.
- **Shape and effects:** the radii, sizes and border width, plus depth and noise.
- **Suggestions** (in the Colours section): click **Suggest colours** for colours
  that go with the current primary (analogous, complementary, triadic) and, if the
  theme has a logo, the logo's main colours. Clicking a suggestion fills in those
  colours for the current mode.

Every change shows on the page straight away (in your browser only).

- **Save draft** stores the panel's values in the theme's draft (needs the
  change permission). Visitors don't see it until it's published. Only the bases,
  colours and shape are changed; the name, branding and mode stay as they are.
- **Publish** (needs `publish_theme`) saves any unsaved changes first, then
  publishes, with an optional note, through the same revisions as the admin's
  Publish page.
- With unsaved changes, the panel says so, and closing it or leaving the page
  asks before throwing them away.

- It edits the active theme, or any theme with `?edit=<theme id>` on any page's
  URL, which also opens the panel straight away.
- The panel is plain CSS and JavaScript (`static/capy_theme/editor/`), not
  Tailwind or daisyUI classes, so it looks the same on any page. The script is a
  static file and the preview uses a constructed stylesheet, so both work under a
  strict Content Security Policy.
- It reads the draft from `/theme/editor/<id>/state/`, and previews unsaved
  values by POSTing them as JSON to `/theme/editor/<id>/preview/`, which returns
  the CSS, every colour's value and the contrast ratings. Both use the same code
  as publishing (so the preview matches what would be published), are for staff
  with change permission only, and **never write anything**. The preview needs
  Django's CSRF token, which the page passes to the script.

### Browser colour, focus outline and email colours

- **Browser colour:** `{% theme_head %}` adds `<meta name="theme-color">` tags, so
  phones colour their address bar to match the page background. There's one per
  mode (chosen by the device), or a single one when a mode is forced.
- **Focus outline:** the stylesheet gives keyboard focus (`:focus-visible`) a 2 px
  outline in `--capy-focus`. That's the primary colour when it has at least 3:1
  contrast with the background (WCAG's minimum for non-text), otherwise the text
  colour, so it's always visible.
- **Email colours:** HTML emails can't use OKLCH or CSS variables, so templates
  get every light-mode colour as hex in `theme.email_colors`, e.g.
  `{{ theme.email_colors.primary }}` or `{{ theme.email_colors.base_100 }}`.

### Fonts

Fonts live in a shared **font library** (admin → Capy Theme → **Fonts**): each
font has a family name, a source, a fallback stack and a licence note, and its
WOFF2 files (one per weight and style, optionally per character subset). Any
theme can use any font.

A theme chooses fonts for four roles, in the **Fonts** section of its admin page
or in the live editor:

| Role | Applies to | CSS |
| --- | --- | --- |
| Body text | the page's text | `--font-sans` (Tailwind's default) and `body` |
| Headings | `h1`–`h6` | `--capy-font-heading` |
| Monospace | `code`, `kbd`, `samp`, `pre` | `--font-mono` |
| Display | elements with the `capy-display` class | `--capy-font-display` |

Roles left on "Default" use the project's own fonts.

**System font stacks** are in the library from the start (added by a migration):
System sans, System serif and System mono, plus ten styles from
[Modern Font Stacks](https://modernfontstacks.com) (CC0): Transitional, Old Style,
Humanist, Geometric Humanist, Neo-Grotesque, Rounded, Slab Serif, Didone,
Monospace Code and Industrial. They use fonts already on the visitor's device,
so **nothing is downloaded**. They're the fastest option.

**Uploading fonts.** On a font's admin page, add files under **Files**: WOFF2,
WOFF, TTF or OTF. Each file is checked with fontTools (anything that isn't a font,
like a renamed image, is refused), converted to WOFF2, and by default trimmed to
the **Latin** characters, which often cuts it to a few percent of its size. Choose
another subset (Latin Extended, Cyrillic, Greek, Vietnamese) or **All characters**
to keep everything. Leave weight and style blank to read them from the font. The
size limit is 5 MB per file (`CAPY_THEME_FONT_MAX_BYTES`).

**Importing from Google Fonts.** On the Fonts list in the admin, click **Import
from Google Fonts**, type a family name (e.g. *Lora*), and pick the weights,
italics and character sets. The server downloads the files **once** and stores
them with your other media, so pages load the font **from your own site**:
visitors' browsers never contact Google. Weights a family doesn't have are skipped.

**External font stylesheets** are for licensed fonts that can't be self-hosted,
like **Adobe Fonts**. Add a font with source **External stylesheet**, the font's
CSS family name as the family (e.g. `proxima-nova`), and the provider's https
stylesheet address (e.g. your Adobe Fonts kit, `https://use.typekit.net/abc1234.css`).
`{% theme_head %}` then links that stylesheet before the theme's own, and the live
editor links it while previewing. The provider's stylesheet defines the font
faces, so the browser loads them from the provider.

If the project uses a **Content Security Policy**, allow the provider's domains:
the stylesheet's domain in `style-src` and the font files' domain in `font-src`.
For Adobe Fonts, with Django 6.1's built-in CSP setting:

```python
from django.utils.csp import CSP

SECURE_CSP = {
    "style-src": [CSP.SELF, "https://use.typekit.net", "https://p.typekit.net"],
    "font-src": [CSP.SELF, "https://use.typekit.net"],
    # ...the project's other directives
}
```

(Self-hosted fonts, which means uploaded, imported, bundled and system ones,
need no extra CSP entries.)

**A curated collection of 30 open-licence fonts** is bundled with the module
(Inter, Roboto, Open Sans, Lato, Montserrat, Source Sans 3, Nunito, Poppins, Work
Sans, IBM Plex Sans, DM Sans, Raleway, Figtree, Manrope, Outfit, Merriweather,
Lora, Playfair Display, Source Serif 4, Libre Baskerville, EB Garamond, Crimson
Pro, PT Serif, IBM Plex Serif, JetBrains Mono, Fira Code, Source Code Pro, IBM
Plex Mono, Oswald and Bebas Neue). Add them to the library with:

```bash
uv run python manage.py capy_theme_add_fonts     # in the demo: uv run python demo/manage.py capy_theme_add_fonts
```

It copies each font's files (Latin regular, bold and italic, where the font has
them) into the project's media storage and adds them to the library. Fonts already
there are skipped, so it's safe to run again. The font list in the admin shows a
preview of each font, and the editor shows a sample under each font choice.

All 30 are under the SIL Open Font License 1.1. Their licence files are in
`src/capy_theme/static/capy_theme/fonts/<font>/LICENSE`. They come from
[Fontsource](https://fontsource.org). To change the collection, edit the list in
`scripts/fetch_curated_fonts.py` and run:

```bash
uv run python scripts/fetch_curated_fonts.py
``` The stylesheet adds an
`@font-face` rule (with `font-display: swap`) for each file. The element rules
are in `@layer base`, so a project's own utility classes, like `font-serif`, still
win. When a theme is published, its fonts' details and file URLs are copied into
the revision, so editing the library later can't change a published theme.

### Type scale

The **Type scale** section (and the editor's "Fonts and type") sets:

| Setting | Range | Effect |
| --- | --- | --- |
| Base text size | 14–24 px | The root font size: body text, and everything sized in rem, scales with it. **At least 14 px**, so text stays readable. |
| Heading scale | 1.05–1.6 | `h6` is 1 rem and each level up multiplies by this (1.25 gives `h1` ≈ 3 rem). |
| Line height | 1.1–2.2 | Space between lines of body text. |
| Heading weight | 100–900 | How bold headings are. |

Blank values leave the project's own styles alone. They're written as variables
(`--capy-base-size`, `--capy-h1` … `--capy-h6`, `--capy-line-height`,
`--capy-heading-weight`) plus default rules in `@layer base`, so utility classes on
an element (like the demo's `text-5xl` headings) still win.

**Font loading:** every `@font-face` uses `font-display: swap`, so text shows
straight away in a fallback font. `{% theme_head %}` also **preloads** the body
and heading fonts' regular files (`<link rel="preload" as="font">`), so the right
font arrives sooner.

### Shape and effects

The **Shape and effects** section overrides daisyUI's shape settings, for both
light and dark mode:

| Setting | daisyUI variable | Range |
| --- | --- | --- |
| Small corner radius (checkboxes, toggles, badges) | `--radius-selector` | 0–2 rem |
| Field corner radius (buttons, inputs, tabs) | `--radius-field` | 0–2 rem |
| Box corner radius (cards, alerts, modals) | `--radius-box` | 0–3 rem |
| Small control size / Field size | `--size-selector` / `--size-field` | 0.125–0.5 rem |
| Border width | `--border` | 0–4 px |
| Depth (3D shadow) / Noise (grain) | `--depth` / `--noise` | on or off |

Blank fields (and "From the base theme") use the base theme's value, which is
shown greyed out. A radius of 0 gives square corners. Stored in
`settings["shape"]`.

### Light and dark mode

On a theme's admin page, the **Mode** section has:

- **Default mode:** *Auto* (follow the visitor's device setting), *Light* or *Dark*.
- **Visitors can switch** (on by default): shows `{% theme_mode_toggle %}`, three
  buttons (Light, Dark, Auto). A visitor's choice is kept in the `capy_theme_mode`
  cookie for a year.

Like everything else, these take effect when the theme is published.

How it works: the server puts `data-theme="capy-light"` or `"capy-dark"` on
`<html>` (`{% theme_html_attrs %}`) when a mode is forced, so pages arrive in the
right mode with no flash. For "auto" it adds nothing, and the stylesheet follows
the device. The script from `{% theme_head %}` does the same before the page
draws (so cached pages are right too) and makes the buttons switch instantly.
Without JavaScript, each button is a link to `/theme/mode/<light|dark|auto>/`,
which sets the cookie and comes back to the page. The script carries Django's
CSP nonce when the project uses Django's CSP middleware.

### Permissions

Editing themes uses Django's normal model permissions (view, add, change, delete
theme). capy-theme adds three more, given to users or groups in the admin under
**Authentication and Authorization**:

| Permission | Allows |
| --- | --- |
| `capy_theme.publish_theme` | Publishing a theme, activating it, and restoring old revisions. Without it, the Publish button and the Activate action are hidden, and direct requests are refused. |
| `capy_theme.edit_custom_css` | Editing a theme's custom CSS (from 8.1). |
| `capy_theme.import_theme` | Importing themes (from 7.3). |

For example, a "Designer" group with view, add and change can edit drafts, while
only an "Editor" group with `publish_theme` as well can make changes live.
Superusers have every permission.

### Drafts and publishing

Editing a theme in the admin changes only its **draft**. Pages will use the
theme's **live revision**, which changes only when someone publishes:

- On a theme's edit page, click **Publish** (needs the `publish_theme` permission). A confirmation page shows what's
  live now and has an optional note box. Publishing copies the draft's look
  (light base, dark base and `settings`) into a new numbered `ThemeRevision`,
  recording who published it and when, and makes it the live revision.
- If the draft matches the live revision, publishing is refused ("Nothing to publish").
- The name and slug aren't part of a revision, so renaming takes effect without publishing.
- Revisions can't be edited or deleted. They're listed on the theme's edit page,
  and removed only if the theme itself is deleted.
- **Revisions** (button on the theme's edit page) lists every revision and
  **compares** any two, showing exactly which values changed (bases, logo,
  branding, mode, each colour and each shape setting).
- **Restore** (needs `publish_theme`) copies an old revision into the draft and
  publishes it **as a new revision**, noted "Restored revision N". Nothing in the
  history is deleted, and the site shows it straight away.

From code: `from capy_theme.publishing import publish` then `publish(theme, user=request.user, note="…")`.

### The active theme

One theme is the site's **active** theme. To choose it, tick it in the admin's
theme list and run the **Activate** action (needs the `publish_theme` permission). The list's "Active" column shows
which one it is. A theme must be published before it can be activated.

From code: `from capy_theme.active import get_active_theme` then
`get_active_theme(request)` returns the active `Theme`, with its live revision
loaded, or `None` if no theme is active. It's cached (see
`CAPY_THEME_CACHE_SECONDS`), so a normal page load doesn't query the database.


### Visitors' accessibility settings

The theme stylesheet respects two device settings, for every page, with nothing
to configure:

- **Reduce motion** (`prefers-reduced-motion: reduce`): animations and
  transitions finish at once and smooth scrolling is off. daisyUI only does this
  for a few components; this covers all of them.
- **More contrast** (`prefers-contrast: more`): no noise texture or depth
  shading, 2 px borders and a 3 px focus outline. The theme's colours stay as
  they are (every colour pair's contrast is already shown in the editor).

To try them: Chrome DevTools → **Rendering** → "Emulate CSS media feature".

### Scheduled themes

A theme can be live between two dates, e.g. a holiday theme. In the admin, go
to **Capy Theme → Theme schedule → Add**, choose a published theme and give a
start and/or end date (blank start: straight away; blank end: until removed).
While a schedule is running (start ≤ now < end) its theme replaces the site's
default; afterwards the default returns by itself. If schedules overlap, the one
that started most recently wins. A visitor's own choice (below) still wins over
both. The list shows each schedule as Upcoming, Running or Finished. Scheduling
needs the `publish_theme` permission, like activating.

The cached theme expires at the next start or end, so schedules switch on time
even with a long `CAPY_THEME_CACHE_SECONDS`.

### Visitor theme picker

Visitors can choose among themes the operator offers:

1. In the admin, tick **Offer to visitors** on each theme to offer, and publish it.
2. Put `{% theme_picker %}` where visitors should choose (the demo has it in a
   **Theme** dropdown in the navbar). It lists **Site default** and the offered
   themes, and outputs nothing if none are offered.

Each option is a link to `/theme/choose/<slug>/` (or `/theme/choose/default/`),
which stores the choice in the `capy_theme_choice` cookie and goes back to the
page. Only offered, published themes are used; any other value in the cookie is
ignored, so visitors can't force a theme. `CAPY_THEME_VISITOR_THEMES = False`
turns the whole feature off. Pages then depend on that cookie, so a project that
caches whole pages must vary its cache on it.
### The theme stylesheet

Each published revision has its own stylesheet at `/theme/<version>.css`, where
`<version>` is a short hash unique to that revision (`ThemeRevision.css_version`).
It sets daisyUI's CSS variables (`--color-primary` and the rest): light values on
`:root`, and dark values inside `@media (prefers-color-scheme: dark)`. The rules
aren't in a CSS layer, so they override daisyUI's own theme rules.

- Browsers cache each stylesheet for a year. Publishing creates a new version,
  so pages link to a new URL and visitors get the change straight away.
- An old URL keeps returning the revision it was made for.
- Pages link it with `?v=<capy-theme version>` on the end (e.g.
  `/theme/52e3f01881d2.css?v=0.1.0`). When an upgrade changes how the module
  writes its CSS, the new version in the link makes browsers fetch it again
  instead of using a copy cached for a year. The view ignores `?v=`.
- The values come from the revision itself, not from today's daisyUI catalogue.
  Each publish saves both base themes' full values, so a later daisyUI update
  can't change or break a published theme. To pick up daisyUI's changes,
  publish again.
- After a daisyUI update (see [Updating daisyUI](#updating-daisyui)), the admin
  shows which published themes are affected. The theme list's "Base changed in
  daisyUI" column ticks them, and each theme's page says whether a base was
  changed or removed. The site keeps using the saved version until someone publishes.

On a theme's admin page, "View its stylesheet" opens the live revision's
stylesheet. Pages link it with `{% theme_head %}` (see [Add it to a project](#add-it-to-a-project)).

### The theme showcase

`/theme/showcase/` shows the active theme on every kind of daisyUI component
(buttons, badges, alerts, cards, tabs, a table, form fields, progress bars, a
modal, headings and text), with light and dark mode side by side. It also has a
swatch for each of the 20 colours (with its text colour, OKLCH and hex values,
contrast rating, and whether it's overridden, worked out or from the base
theme), and samples of every shape setting, and a **Fonts and type** section: each role's font
and source with a sample in every weight and style that's actually loaded (so
nothing shown is a browser-faked bold), the heading scale, body text at the base
size with its line height, a monospace code block, and a character sample for
the fonts' character sets. It also shows
the site name, tagline, logo and the base themes in use; a **Mode and visitors**
panel (the default mode, the light/dark/auto toggle, the visitor theme picker,
and the upcoming and running scheduled themes with their dates); and an **Images and
icons** section: every logo slot at the header height in both modes (saying
whether it's its own image, the light one, or what an empty slot falls back to)
with its generated sizes and formats; every icon at its real size (the maskable
icon inside a circle and a squircle, the monochrome icon on a dark tile); the
sharing image; and the background images. Staff only by default
(see `CAPY_THEME_SHOWCASE`). The demo's navbar links to it.

Each section is its own template in
`src/capy_theme/templates/capy_theme/showcase/sections/`, listed in
`SHOWCASE_SECTIONS` in `views.py`. To add a section, add a template there and
its name to the list. It's included once per mode, with `mode` set to `"light"`
or `"dark"`, so use `{{ mode }}` in any `id` or `name` that must be unique.

The showcase brings its own stylesheet, `src/capy_theme/static/capy_theme/showcase.css`
(daisyUI plus the Tailwind classes the showcase templates use), so it works in
any project. It's built from the showcase templates, so **rebuild it after
changing them** (or after updating daisyUI):

```bash
uv run python scripts/build_showcase_css.py
```

It uses the Tailwind CLI that the demo downloads. If it says the CLI isn't found,
run `uv run python demo/manage.py tailwind build` once first.

## Build the package

To build the installable package (a wheel and an sdist, written to `dist/`) and
check what's in it:

```bash
uv build
unzip -l dist/capy_theme-*.whl     # should list only capy_theme/ files, nothing from demo/ or scripts/
```

`dist/` is git-ignored.

## Release a version

Each release has its own issue (e.g. "1.10 Release v0.1.0"). Before it, run
the tests on SQLite and on Postgres (above), and check the package with
`uv build` (see [Build the package](#build-the-package)). Nothing is pushed
straight to `main`:

1. On the release issue's branch, change `version` in `pyproject.toml` and add an
   entry to `CHANGELOG.md`. Commit, push the branch and open a PR that closes the issue.
2. After the PR is merged, tag the merged `main` and push only the tag:

   ```bash
   git checkout main
   git pull
   git tag v0.2.0
   git push origin v0.2.0
   ```

3. In each project, update the tag in its `uv add` line when you want the new version.

## Rules that keep it pluggable

- Never import from a project or from another module.
- Link to users with `settings.AUTH_USER_MODEL`, never a project's `User` class.
- Keep templates in `src/capy_theme/templates/capy_theme/` and static
  files in `src/capy_theme/static/capy_theme/`, so names never clash.
- Read any settings the project can change with a `CAPY_THEME_` prefix
  and a sensible default, e.g. `getattr(settings, "CAPY_THEME_CACHE_SECONDS", 300)`.

## Files

| Path | Purpose |
| --- | --- |
| `src/capy_theme/` | The Django app that projects install |
| `src/capy_theme/apps.py` | The app's name, label and admin title |
| `src/capy_theme/models.py` | Database models: `Font` and `FontFile` (the font library), `ThemeAsset` and `ThemeAssetVariant` (a theme's uploaded images and their generated sizes), `Theme` (the draft: name, slug, light and dark base, `settings` overrides, and its live revision) `ThemeRevision` (a published copy of a theme's look) and `ThemeAssignment` (which theme is active) |
| `src/capy_theme/stylesheet.py` | Writes a published revision out as CSS variables, and makes its version hash |
| `src/capy_theme/views.py` | The stylesheet view (`/theme/<version>.css`), the showcase (`/theme/showcase/`), the mode switch (`/theme/mode/<mode>/`) and the live editor's JSON views |
| `src/capy_theme/urls.py` | The module's URLs, included by projects under `/theme/` |
| `src/capy_theme/templatetags/capy_theme.py` | The `{% theme_head %}`, `{% theme_html_attrs %}`, `{% theme_logo %}`, `{% theme_mode_toggle %}`, `{% theme_picker %}` and `{% theme_artifacts %}` template tags |
| `src/capy_theme/branding.py` | Reads a revision's published site name, tagline and logo |
| `src/capy_theme/context_processors.py` | Gives every template `theme`: the active theme's published values (or `None`) |
| `src/capy_theme/templates/capy_theme/showcase/` | The showcase page, its standalone base page, and one template per section |
| `src/capy_theme/static/capy_theme/showcase.css` | The showcase's bundled stylesheet (built; don't edit) |
| `scripts/build_showcase_css.py`, `scripts/showcase.tailwind.css` | Build `showcase.css` with Tailwind and daisyUI |
| `src/capy_theme/colors.py` | The 20 overridable colours, their groups, and merging overrides over the base theme |
| `src/capy_theme/forms.py` | `ColorField`: accepts any colour format, with the browser's colour picker (`static/capy_theme/admin/color_input.js`) |
| `src/capy_theme/shape.py` | The shape and effect settings (radii, sizes, border, depth, noise) |
| `src/capy_theme/showcase.py` | Data for the showcase's colour swatches and shape samples |
| `src/capy_theme/editor.py` | The live editor: who can use it, which theme it edits, and the draft data it reads |
| `src/capy_theme/static/capy_theme/editor/` | The editor panel: `editor.js` (panel, preview), `editor-controls.js` (bases, colours, fonts, images, shape) and `editor.css` |
| `src/capy_theme/templates/capy_theme/editor/mount.html` | Loads the editor on a page for staff who can edit |
| `src/capy_theme/palette.py` | Colour suggestions from a primary colour or from the logo |
| `src/capy_theme/history.py` | Comparing two revisions and restoring an old one |
| `src/capy_theme/fonts.py` | Font roles, copying fonts into revisions, and the `@font-face` and font CSS |
| `src/capy_theme/curated_fonts.json`, `src/capy_theme/static/capy_theme/fonts/` | The curated font collection (WOFF2 files and licences) |
| `src/capy_theme/management/commands/capy_theme_add_fonts.py` | Adds the curated fonts to the font library |
| `scripts/fetch_curated_fonts.py` | Fetches the curated fonts from Fontsource |
| `src/capy_theme/font_files.py` | Checks uploaded font files, converts them to WOFF2 and trims them to a character subset |
| `src/capy_theme/google_fonts.py` | Imports a Google font into the library (downloaded once, served locally) |
| `src/capy_theme/images.py` | Image slots and their limits, and checking and cleaning uploaded images |
| `src/capy_theme/accessibility.py` | The reduce-motion and more-contrast CSS |
| `src/capy_theme/backgrounds.py` | The background image CSS variables, helper classes and template values |
| `src/capy_theme/artifacts.py` | `get_artifacts()`: every published theme artifact as plain data for other modules |
| `src/capy_theme/social.py` | The 1200 × 630 sharing image |
| `src/capy_theme/icons.py` | Makes the favicons and app icons from the icon image, and their `<link>` tags |
| `src/capy_theme/logos.py` | Logo slots: fallbacks, smaller copies, the `<picture>` HTML and the header height CSS |
| `src/capy_theme/svg.py` | Cleaning uploaded SVGs with an allow-list of elements and attributes |
| `src/capy_theme/typography.py` | The type scale settings and their CSS |
| `src/capy_theme/mode.py` | Light/dark/auto: the theme's mode settings, the visitor's cookie, and the head script |
| `src/capy_theme/templates/capy_theme/theme_picker.html` | The theme list for `{% theme_picker %}` |
| `src/capy_theme/templates/capy_theme/mode_toggle.html` | The Light / Dark / Auto buttons for `{% theme_mode_toggle %}` |
| `src/capy_theme/active.py` | `get_active_theme()` (cached) and `activate()`: which theme the site uses |
| `src/capy_theme/signals.py` | Clears the active-theme cache whenever themes, revisions or assignments change |
| `src/capy_theme/publishing.py` | `publish()`: turns a theme's draft into its new live revision |
| `src/capy_theme/admin.py` | The admin pages for themes, including the Publish page and the list of published revisions |
| `src/capy_theme/templates/capy_theme/admin/` | Templates for the theme edit page (adds the Publish button) and the Publish page |
| `src/capy_theme/settings.schema.json` | JSON Schema that every theme's `settings` must match |
| `src/capy_theme/validation.py` | Checks `settings` against the schema, and that bases are valid themes |
| `src/capy_theme/migrations/` | Database migrations (create with the `makemigrations` command above) |
| `src/capy_theme/builtin_themes.py` | daisyUI's built-in themes and their values (generated; don't edit) |
| `src/capy_theme/catalogue.py` | `get_builtin_themes()`: the built-in themes a project offers |
| `scripts/generate_builtin_themes.py` | Regenerates `builtin_themes.py` from the daisyUI package |
| `demo/` | The demo site, for development only (not in the package) |
| `tests/settings.py` | A tiny stand-in project for the tests |
| `tests/test_app.py` | Checks the app loads and its migrations are complete |
| `docs/PLAN.md` | The build plan: every phase and step |
| `docs/DECISIONS.md` | Every design decision made while building, with the alternatives and why |
| `pyproject.toml` | Package name, version, Django versions supported, tool settings |
| `CHANGELOG.md` | What changed in each version |
| `.copier-answers.yml` | Lets `copier update` find the template; don't edit |
