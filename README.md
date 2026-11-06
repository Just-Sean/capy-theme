# Capy Theme

Theming for Django projects.

A self-contained Django app (`capy_theme`) that any Django 6.1+ project
can install. It has no project of its own: its tests run against a tiny
stand-in project in `tests/`.

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

3. Create its database tables:

   ```bash
   uv run python manage.py migrate
   ```

The module's tables go into whatever database the project uses.

## Develop it

```bash
uv sync                    # installs Python, Django and the test tools
uv run pytest              # runs the tests on SQLite, no setup needed
uv run ruff check .        # finds problems
uv run ruff format .       # formats the code
```

To run the tests on Postgres instead (for Postgres-only features):

```bash
DATABASE_URL=postgres://app:app@localhost:5432/module_tests uv run pytest
```

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

It uses SQLite (`demo/db.sqlite3`) by default; set `DATABASE_URL` to use Postgres.

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
files (`daisyui.mjs`, `daisyui-theme.mjs`) kept next to it. To update daisyUI,
replace those two files with ones from a newer
[daisyUI release](https://github.com/saadeghi/daisyui/releases).

To create migrations after changing models, run Django's command against the
test project:

```bash
uv run django-admin makemigrations capy_theme --settings=tests.settings --pythonpath=.
```

## Release a version

Each release has its own issue (e.g. "1.10 Release v0.1.0"). Nothing is pushed
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
| `src/capy_theme/models.py` | Database models (empty to start) |
| `tests/settings.py` | A tiny stand-in project for the tests |
| `tests/test_app.py` | Checks the app loads and its migrations are complete |
| `pyproject.toml` | Package name, version, Django versions supported, tool settings |
| `CHANGELOG.md` | What changed in each version |
| `.copier-answers.yml` | Lets `copier update` find the template; don't edit |
