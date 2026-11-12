# Capy Theme

Theming for Django projects.

A self-contained Django app (`capy_theme`) that any Django 6.1+ project
can install. It has no project of its own: its tests run against a tiny
stand-in project in `tests/`, and `demo/` is a small site for trying it out.

## What it does (v0.7)

Whoever runs the site controls its look from the Django admin, with no code
changes or redeploys. The project needs a Tailwind CSS 4 / daisyUI 5 stylesheet.

- **Live theme editor:** staff edit a theme right on the page (any page using
  `{% theme_head %}`), with colour pickers, shape controls, contrast
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
- **Theme artifacts for other apps:** `get_artifacts()` (and
  `{% theme_artifacts %}`) give every colour, font, logo, icon and image as plain
  data, so an email module, app shell or PWA module can use the theme. capy-theme
  doesn't apply them outside the page's own look.
- **JSON API and downloads** for front ends, apps and design tools:
  `/theme/api.json` (with ETag; a DRF view documented by drf-spectacular when the
  project uses DRF), W3C design tokens and daisyUI theme blocks. See
  [docs/developers.md](docs/developers.md).
- **Export and import** a theme between sites (admin buttons or management
  commands), arriving as a draft.
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
- **Components view** in the editor: every daisyUI component and the theme's
  images and icons in the draft theme, light and dark side by side, updating as
  you edit. **See it as a visitor** shows the published theme instead, by mode,
  offered theme or date.
- **Permissions:** only users with `publish_theme` can publish or activate.

Next: custom CSS, multiple sites, project settings and 1.0 (see `docs/PLAN.md`).

## Add it to a project

1. Install it, from a folder next to your project or from GitHub:

   ```bash
   uv add --editable ../capy-theme                     # while developing it
   uv add git+https://github.com/Just-Sean/capy-theme --tag vX.Y.Z   # a pinned release: use the latest tag
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
   `capy_theme/templates` folder. This prints where that is:

   ```bash
   uv run python -c "import capy_theme, pathlib; print(pathlib.Path(capy_theme.__file__).parent / 'templates')"
   ```

   If the project doesn't have Tailwind CSS and daisyUI yet, see
   [Tailwind and daisyUI for a new project](#tailwind-and-daisyui-for-a-new-project) below.

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
[Logos](docs/images.md#logos)). Extra attributes go on the `<img>`, e.g.
`{% theme_logo class="me-2" %}`. Every template also gets a `theme` variable
holding the published `site_name`, `tagline`, `logo_url`, `logo_alt`, `name`,
`slug`, `revision`, `light_base`, `dark_base`, `stylesheet_url`, `default_mode`,
`visitors_can_switch`, `mode` (what this visitor sees), `email_colors` (hex),
`background_login_url` and `background_pattern_url`, or `None`
if no theme is active.

Pages then show the **active** theme's **published** colours. Until a theme is
published and activated in the admin, they show daisyUI's defaults.

The module's tables go into whatever database the project uses.

### Tailwind and daisyUI for a new project

capy-theme themes a daisyUI 5 stylesheet; it doesn't build one. A project without
Tailwind CSS can add it without Node, with django-tailwind-cli (the same set-up as
the demo):

1. Install it and the daisyUI plugin files:

   ```bash
   uv add django-tailwind-cli
   mkdir -p tailwind static
   gh release download v5.7.50 --repo saadeghi/daisyui -p daisyui.mjs -p daisyui-theme.mjs -D tailwind
   ```

2. In `settings.py`, add `"django_tailwind_cli"` to `INSTALLED_APPS`, and:

   ```python
   STATICFILES_DIRS = [BASE_DIR / "static"]
   TAILWIND_CLI_VERSION = "4.3.4"
   TAILWIND_CLI_SRC_CSS = "tailwind/source.css"
   TAILWIND_CLI_DIST_CSS = "css/site.css"
   ```

3. Create `tailwind/source.css`, with your templates and capy-theme's (the path
   printed by the command above, relative to `tailwind/`):

   ```css
   @import "tailwindcss";
   @source "../templates";
   @source "../.venv/lib/python3.14/site-packages/capy_theme/templates";
   @plugin "./daisyui.mjs";
   ```

4. Link it in the base template, before `{% theme_head %}`:
   `<link rel="stylesheet" href="{% static 'css/site.css' %}">`, then build it:

   ```bash
   uv run python manage.py tailwind build       # once, or for production
   uv run python manage.py tailwind runserver   # while developing: rebuilds on changes
   ```

## Settings

Optional settings a project can add to its `settings.py` (all defaults are in
`src/capy_theme/conf.py`):

| Setting | Default | What it does |
| --- | --- | --- |
| `CAPY_THEME_BUILTIN_THEMES` | all 35 | Which built-in daisyUI themes can be used as a theme's light or dark base, e.g. `["light", "dark"]`. Listing an unknown theme raises an error that names it. |
| `CAPY_THEME_CACHE_SECONDS` | `300` | How long the active theme is cached, in seconds. Publishing or activating clears the cache straight away; this limit makes every server process catch up when the project's cache isn't shared between processes (e.g. Django's default in-memory cache). |
| `CAPY_THEME_API` | `"auto"` | How `/theme/api.json` is served: `"auto"` (a DRF view if Django REST Framework is installed, so drf-spectacular documents it; otherwise a plain Django view), `"drf"` or `"django"`. See [docs/artifacts.md](docs/artifacts.md). |
| `CAPY_THEME_CUSTOM_CSS` | `True` | Allow custom CSS. `False` switches it off for the whole project: no theme's custom CSS is loaded, and nobody (not even superusers) sees the Custom CSS section. See [docs/colors-and-css.md](docs/colors-and-css.md#custom-css). |
| `CAPY_THEME_VISITOR_THEMES` | `True` | Let visitors choose among the themes offered to them with `{% theme_picker %}`. `False` turns the picker off and ignores visitors' choices. |
| `CAPY_THEME_EDITOR_BUTTON` | `True` | Show the live editor's **Edit theme** button in the corner of every page, for staff who can edit. `False` hides it (the editor still opens with `?edit=<theme id>`, e.g. from **Edit live** in the admin). |
| `CAPY_THEME_FONT_MAX_BYTES` | `5242880` (5 MB) | The largest font file that can be uploaded, in bytes. |
| `CAPY_THEME_IMAGE_MAX_BYTES` | `None` (each slot's own limit) | A cap on every image upload, in bytes. Each slot keeps its own limit (1 to 5 MB, in `images/slots.json`) when that's lower. |
| `CAPY_THEME_ANIMATION_MAX_FRAMES` | `500` | The most frames an uploaded animated image (GIF) can have. |
| `CAPY_THEME_ANIMATION_MAX_PIXELS` | `100000000` (100 million) | The most pixels an uploaded animated image can have in all (frames × width × height). Each frame is decoded at full size when the image is saved again, so this caps the memory one upload can use (about 75 MB at the default). |
| `CAPY_THEME_IMPORT_MAX_BYTES` | `52428800` (50 MB) | The largest theme import (all files in the zip, unpacked), in bytes. |

## Develop it

```bash
uv sync                    # installs Python, Django and the test tools
uv run pre-commit install  # checks every commit for secrets and lint (once per clone; see below)
uv run pytest              # runs the tests on SQLite, no setup needed
uv run pytest --cov        # the same, plus which lines the tests never run
uv run ruff check .        # finds problems
uv run ruff format .       # formats the code
# before every PR, also check dependencies with pip-audit (see "Dependency vulnerabilities and test coverage" below)
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

### Checks on every commit (pre-commit)

`.pre-commit-config.yaml` runs these checks each time you commit, and blocks the
commit if one fails:

- **gitleaks**: finds passwords, keys and tokens in the changes being committed.
- **ruff check** and **ruff format --check**: lint and formatting, with the
  project's own ruff.

Set it up once in each clone, after `uv sync`:

```bash
uv run pre-commit install          # runs the checks on every commit from now on
uv run pre-commit run --all-files  # runs ruff on every file, any time
```

gitleaks only looks at what's staged for a commit, so `--all-files` doesn't scan
anything for secrets. To scan **every file** or the **whole git history**, use
gitleaks' official Docker image (the same version as the hook, pinned to its exact
image, with the repo mounted read-only):

```bash
docker run --rm -v "$PWD:/repo:ro" ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f dir /repo --redact   # every file
docker run --rm -v "$PWD:/repo:ro" ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f git /repo --redact   # the whole history
```

If gitleaks blocks a commit, remove the secret instead of skipping the check. If
the secret was ever pushed, treat it as leaked and replace it.

If a ruff check fails with "files were modified by this hook" and `uv.lock` has
changed, `pyproject.toml` was changed without updating the lock file (`uv run`
updated it). Stage `uv.lock` and commit again.

**Updating gitleaks:** the hook is pinned to a commit, not a tag, because tags can
be moved. Run `uv run pre-commit autoupdate --freeze` and check the version in its
`# frozen:` comment (it can pick an older tag; if so, set the commit of the version
you want by hand). Then update the Docker commands above, and `GITLEAKS_IMAGE` in
`.github/workflows/ci.yml`, to the same version and its digest (`docker pull ghcr.io/gitleaks/gitleaks:<version>`, then
`docker inspect ghcr.io/gitleaks/gitleaks:<version> --format '{{index .RepoDigests 0}}'`).

### Dependency vulnerabilities and test coverage

Before every PR, check the dependencies for known security problems and look at
what the tests cover:

```bash
(f=$(mktemp) && trap 'rm -f "$f"' EXIT && uv export --locked --format requirements-txt --no-emit-project --quiet -o "$f" && uv run pip-audit --disable-pip --require-hashes -r "$f")
uv run pytest --cov
```

- **pip-audit** checks the packages in `uv.lock` (their exact versions and hashes,
  including the dev tools) against the public vulnerability databases. It prints
  "No known vulnerabilities found", or each problem with the version that fixes
  it. The usual fix is upgrading that package (`uv lock --upgrade-package
  <name>`), as its own change.
  - The command writes the lock file's packages to a temporary file first, so if
    that step fails (e.g. `uv.lock` is out of date with `pyproject.toml`, which
    `--locked` treats as an error) the whole command fails instead of auditing
    nothing.
  - It only checks packages used on **this** platform. On Linux with standard
    Python it skips `tzdata` and `colorama` (Windows only) and `brotlicffi`,
    `cffi` and `pycparser` (PyPy only).
  - It doesn't cover the build tool (`uv_build`), uv itself, or the gitleaks hook.
- **Coverage** is set up in `pyproject.toml` (`[tool.coverage.*]`): it measures
  `capy_theme` (not the migrations), checks both sides of every `if`, and lists
  the lines no test runs, leaving fully covered files out. **`uv run pytest --cov`
  fails if total coverage drops below 80%.** Plain `uv run pytest` doesn't measure
  coverage, so it never fails for this. `uv run pytest --cov --cov-report=html`
  also writes a browsable report to `htmlcov/` (git-ignored).

### Checks on every PR (GitHub Actions)

`.github/workflows/ci.yml` runs the same checks on GitHub for every pull request
and every push to `main`, so every PR shows whether they pass, even if someone
skipped the hooks locally. The results are on the PR's **Checks** tab (and the
repo's **Actions** tab). Each check is its own job:

- **Lint:** `ruff check` and `ruff format --check`.
- **Tests:** `pytest --cov -rs` (fails below 80% coverage; lists any skipped
  tests), once on **SQLite** and once on **Postgres 17**. It downloads the
  Tailwind CLI first and checks it against Tailwind's published SHA-256, so the
  daisyUI build test runs (instead of being skipped) with a verified binary.
- **Dependency vulnerabilities:** the pip-audit command above.
- **Secrets:** gitleaks over the whole git history, with the same pinned image as
  the commands above.

The workflow can only read the repo, and every action in it is pinned to a commit
hash (with its version in a comment). When updating:

- **gitleaks:** change `GITLEAKS_IMAGE` in the workflow too.
- **uv:** change `UV_VERSION` in the workflow.
- **the Tailwind CLI** (`TAILWIND_CLI_VERSION` in `demo/demo_site/settings.py`):
  change `TAILWIND_CLI` and `TAILWIND_CLI_SHA256` in the workflow. The hash is the
  `tailwindcss-linux-x64` line of that release's `sha256sums.txt`:
  `gh release download v<version> --repo tailwindlabs/tailwindcss -p sha256sums.txt -O - | grep linux-x64$`

## Commands

Every command in one place. Details are in the linked pages.

| Command | What it does |
| --- | --- |
| `uv sync` | Install Python, Django and the test tools |
| `uv run pytest` | Run the tests (SQLite) |
| `DATABASE_URL=postgres://… uv run pytest` | Run the tests on Postgres (see above for a throwaway Docker database) |
| `uv run ruff check .` / `uv run ruff format .` | Lint / format |
| `uv run pytest --cov` | Run the tests, show which lines they never run, and fail below 80% coverage |
| `(f=$(mktemp) && trap 'rm -f "$f"' EXIT && uv export --locked --format requirements-txt --no-emit-project --quiet -o "$f" && uv run pip-audit --disable-pip --require-hashes -r "$f")` | Check the locked dependencies for known vulnerabilities |
| `uv run pre-commit install` | Run gitleaks and ruff on every commit (once per clone) |
| `uv run pre-commit run --all-files` | Run ruff on every file (gitleaks only checks staged changes) |
| `docker run --rm -v "$PWD:/repo:ro" ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f dir /repo --redact` | Scan every file for secrets |
| `docker run --rm -v "$PWD:/repo:ro" ghcr.io/gitleaks/gitleaks:v8.30.1@sha256:c00b6bd0aeb3071cbcb79009cb16a60dd9e0a7c60e2be9ab65d25e6bc8abbb7f git /repo --redact` | Scan the whole git history for secrets |
| `uv run pre-commit autoupdate --freeze` | Update the gitleaks hook (see "Updating gitleaks") |
| `uv run django-admin makemigrations capy_theme --settings=tests.settings --pythonpath=.` | Make migrations after changing a model |
| `uv run python demo/manage.py migrate` | Create or update the demo database |
| `uv run python demo/manage.py createsuperuser` | Make a demo admin account |
| `uv run python demo/manage.py tailwind runserver` | Run the demo site at http://localhost:8000/ (with Tailwind) |
| `uv run python demo/manage.py runserver` | Run the demo without rebuilding Tailwind |
| `uv run python manage.py tailwind build` / `tailwind runserver` | Build the project's Tailwind/daisyUI stylesheet, or run the server rebuilding it (projects using django-tailwind-cli, [below](#tailwind-and-daisyui-for-a-new-project)) |
| `uv run python manage.py theme_export <slug> [-o FILE]` | Export a theme as a zip ([themes](docs/themes.md#from-the-command-line)) |
| `uv run python manage.py theme_import FILE [--publish] [--activate]` | Import an exported theme (as a draft, or published and made the site's theme) |
| `uv run python manage.py theme_publish <slug> [--note TEXT] [--activate]` | Publish a theme's draft (and optionally make it the site's theme) |
| `uv run python manage.py theme_rebuild_images [<slug>]` | Remake logo copies, sharing-image crops and icons (after an update, or for logos from before 0.5) |
| `uv run python manage.py capy_theme_add_fonts` | Add the 30 bundled fonts to a project's font library ([fonts](docs/fonts.md)) |
| `uv run python scripts/fetch_curated_fonts.py` | Re-download the bundled fonts from Fontsource ([fonts](docs/fonts.md)) |
| `uv run python scripts/generate_builtin_themes.py` | Regenerate daisyUI's built-in themes after a daisyUI update ([development](docs/development.md)) |
| `uv run python scripts/build_components_css.py` | Rebuild the Components view's stylesheet ([editor](docs/editor.md)) |
| `gh release download v5.7.50 --repo saadeghi/daisyui -p daisyui.mjs -p daisyui-theme.mjs` | Download daisyUI's plugin files for the demo when updating daisyUI ([development](docs/development.md)) |
| `curl -sSfL -o tests/artifacts/dtcg/format-2025.10.json https://www.designtokens.org/schemas/2025.10/format.json` | Refresh the Design Tokens format schema the tests use ([tests/artifacts/dtcg](tests/artifacts/dtcg/README.md)) |
| `uv build` | Build the package ([below](#build-the-package)) |
| `git tag vX.Y.Z && git push origin vX.Y.Z` | Tag a release ([below](#release-a-version)) |

## Documentation

| Page | About |
| --- | --- |
| [docs/themes.md](docs/themes.md) | Theme settings, the admin page, branding, drafts and publishing, the live theme, scheduling, the visitor theme picker, multiple sites, light and dark mode, permissions, export and import |
| [docs/colors-and-css.md](docs/colors-and-css.md) | Colours and contrast, address-bar/focus/email colours, type scale, shape, accessibility settings, the theme stylesheet, custom CSS |
| [docs/fonts.md](docs/fonts.md) | The font library: system stacks, bundled fonts, uploads, Google Fonts, external stylesheets |
| [docs/images.md](docs/images.md) | Uploads and SVG cleaning, logo slots, icons, the sharing image, backgrounds |
| [docs/editor.md](docs/editor.md) | The live editor and its Components view |
| [docs/artifacts.md](docs/artifacts.md) | What other apps get: `get_artifacts()`, `{% theme_artifacts %}` and the JSON API (`/theme/api.json`, with DRF/drf-spectacular support) the design tokens download (`/theme/tokens.json`) and daisyUI theme blocks (`/theme/daisyui-theme.css`) |
| [docs/developers.md](docs/developers.md) | **For developers using the theme from their own code:** every CSS variable, the JSON API with an example, the downloads |
| [docs/development.md](docs/development.md) | The demo site and updating daisyUI |
| [docs/PLAN.md](docs/PLAN.md), [docs/DECISIONS.md](docs/DECISIONS.md) | The build plan, and why things are the way they are |

## Upgrading

Run `uv run python manage.py migrate` after every update. Version notes:

- **From 0.5:** migration `0011_remove_app_and_social_settings` removes the web
  app manifest and link-preview settings (the manifest view and the tags are
  gone; the icons and sharing image stay, available through the artifacts and
  the API).
- **From 0.4:** migration `0010_logo_slots` moves each theme's old logo into its
  main slot (light). Make its smaller copies with
  `uv run python manage.py theme_rebuild_images`. Revisions published before 0.5
  keep showing their old logo until the theme is published again.
- **From 0.6:** the showcase page and its settings (`CAPY_THEME_SHOWCASE`,
  `CAPY_THEME_BASE_TEMPLATE`) are gone; remove them from your settings. The
  editor's **Show all components** replaces it.

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

## Code layout

One Django app, `capy_theme`, organised in sections. Each Python file does one
job and stays under 200 lines.

| Folder (in `src/capy_theme/`) | What's in it |
| --- | --- |
| `portability/` | Exporting a theme to a zip and importing it as a draft (with the export file's schema) |
| `themes/` | The `Theme`, `ThemeRevision` and assignment models (`models/`), settings validation (+ `settings.schema.json`), daisyUI's built-in themes (`catalogue.py`, `builtin_themes.json`, generated), which theme is live and the cache (`active.py`), publishing, history (compare and restore), light/dark mode, branding, signals, and the mode and theme-choice views |
| `colors/` | Colour names and groups, colour maths (OKLCH, contrast, readable text, shades), a theme's colour values, palette suggestions, the colour form field |
| `css/` | Writing the theme stylesheet: `stylesheet.py` plus shape, type scale, backgrounds, accessibility; and the view that serves it |
| `fonts/` | `Font` and `FontFile` models, the library (roles, stacks, `@font-face`), uploads, Google Fonts import, `curated.json` |
| `images/` | `ThemeAsset` and `ThemeAssetVariant` models, image slots, upload checks, SVG cleaning, logo slots, logo copies, the `{% theme_logo %}` HTML, icons, the sharing image |
| `editor/` | The live editor: who can use it, its state and controls, preview, saving, adding it to pages, its JSON views and the Components view |
| `artifacts/` | `get_artifacts()`: everything other apps get, and the JSON API (plain Django and DRF views) |
| `admin/` | The theme form (one file per area: colours, type, shape, images), the theme admin page and its fieldsets, the Publish/Revisions/Restore pages, inlines, fonts, the theme schedule |
| `templatetags/capy_theme.py` | The template tags; each calls its section |
| `models.py`, `urls.py`, `apps.py`, `context_processors.py` | Django's entry points |
| `templates/capy_theme/`, `static/capy_theme/` | Templates and static files (the editor's JavaScript is one file per section in `static/capy_theme/editor/controls/`) |
| `migrations/`, `management/commands/` | Database migrations and the `capy_theme_add_fonts` command |

Outside the package: `tests/` (in the same sections), `demo/` (development only,
never shipped), `scripts/` (generate daisyUI's themes, fetch the bundled fonts,
build the Components view's CSS), `docs/`.
