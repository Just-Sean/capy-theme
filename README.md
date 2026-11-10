# Capy Theme

Theming for Django projects.

A self-contained Django app (`capy_theme`) that any Django 6.1+ project
can install. It has no project of its own: its tests run against a tiny
stand-in project in `tests/`, and `demo/` is a small site for trying it out.

## What it does (v0.1)

Whoever runs the site controls its look from the Django admin, with no code
changes or redeploys. The project needs a Tailwind CSS 4 / daisyUI 5 stylesheet.

- **Themes** are based on any of daisyUI's 35 built-in themes: one light base and
  one dark base. A project can limit which are offered.
- **Branding:** each theme has a site name, tagline and main logo (with alt text).
- **Drafts and publishing:** editing a theme changes only its draft. Publishing
  saves a numbered revision, recording who published it and when, and the site
  shows that. Every revision is kept.
- **One active theme:** pick it with the admin's Activate action. It's cached, so
  pages don't query the database for it.
- **On every page:** `{% theme_head %}` links the theme's stylesheet (light and dark
  values), `{% theme_logo %}` shows the logo or site name, and every template
  gets a `theme` variable.
- **Light and dark mode:** follow the device or force one, and visitors can switch
  with `{% theme_mode_toggle %}`, with no flash on page load.
- **Theme showcase** at `/theme/showcase/`: every daisyUI component in the
  active theme, with light and dark side by side (staff only by default).
- **Permissions:** only users with `publish_theme` can publish or activate.

Colour, font, shape and image settings, an editor with live preview, scheduling,
an API and more come in later versions (see `docs/PLAN.md`).

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
     <nav>... {% theme_logo class="h-8" %} ... {% theme_mode_toggle %} ...</nav>
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
`{% theme_logo %}`. Extra attributes are passed through, e.g.
`{% theme_logo class="h-8" %}`. Every template also gets a `theme` variable
holding the published `site_name`, `tagline`, `logo_url`, `logo_alt`, `name`,
`slug`, `revision`, `light_base`, `dark_base`, `stylesheet_url`, `default_mode`,
`visitors_can_switch` and `mode` (what this visitor sees), or `None`
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

### Branding

On a theme's admin page, the **Branding** section has the site name, tagline,
logo and logo alt text. The site name, tagline and alt text are stored in the
theme's `settings`. The logo is an image upload (PNG, JPEG, GIF or WebP, checked
with Pillow) saved under `MEDIA_ROOT/capy_theme/logos/`, at the size it's
uploaded. Resized and SVG logos come in Phase 5.

Like everything else, branding changes show on the site only after publishing.
Replacing a logo stores a new file and never overwrites the old one, so older
revisions keep their logo.

The "Overrides" section shows the theme's stored `settings` as read-only JSON.
They're edited through the fields above, not typed by hand.

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
| `capy_theme.publish_theme` | Publishing a theme, activating it, and (from 3.7) restoring old revisions. Without it, the Publish button and the Activate action are hidden, and direct requests are refused. |
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

From code: `from capy_theme.publishing import publish` then `publish(theme, user=request.user, note="…")`.

### The active theme

One theme is the site's **active** theme. To choose it, tick it in the admin's
theme list and run the **Activate** action (needs the `publish_theme` permission). The list's "Active" column shows
which one it is. A theme must be published before it can be activated.

From code: `from capy_theme.active import get_active_theme` then
`get_active_theme(request)` returns the active `Theme`, with its live revision
loaded, or `None` if no theme is active. It's cached (see
`CAPY_THEME_CACHE_SECONDS`), so a normal page load doesn't query the database.

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
modal, headings and text), with light and dark mode side by side. It also shows
the site name, tagline, logo and the base themes in use. Staff only by default
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
| `src/capy_theme/models.py` | Database models: `Theme` (the draft: name, slug, light and dark base, `settings` overrides, and its live revision) `ThemeRevision` (a published copy of a theme's look) and `ThemeAssignment` (which theme is active) |
| `src/capy_theme/stylesheet.py` | Writes a published revision out as CSS variables, and makes its version hash |
| `src/capy_theme/views.py` | The stylesheet view (`/theme/<version>.css`), the showcase (`/theme/showcase/`) and the mode switch (`/theme/mode/<mode>/`) |
| `src/capy_theme/urls.py` | The module's URLs, included by projects under `/theme/` |
| `src/capy_theme/templatetags/capy_theme.py` | The `{% theme_head %}`, `{% theme_html_attrs %}`, `{% theme_logo %}` and `{% theme_mode_toggle %}` template tags |
| `src/capy_theme/branding.py` | Reads a revision's published site name, tagline and logo |
| `src/capy_theme/context_processors.py` | Gives every template `theme`: the active theme's published values (or `None`) |
| `src/capy_theme/templates/capy_theme/showcase/` | The showcase page, its standalone base page, and one template per section |
| `src/capy_theme/static/capy_theme/showcase.css` | The showcase's bundled stylesheet (built; don't edit) |
| `scripts/build_showcase_css.py`, `scripts/showcase.tailwind.css` | Build `showcase.css` with Tailwind and daisyUI |
| `src/capy_theme/mode.py` | Light/dark/auto: the theme's mode settings, the visitor's cookie, and the head script |
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
