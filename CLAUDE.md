# capy-theme

A reusable Django app (`capy_theme`) for theming any Django project with a daisyUI 5 stylesheet. The build plan is in `docs/PLAN.md`, and each step is a GitHub issue in `Just-Sean/capy-theme`.

## How we work

- One issue at a time, in order. Build only what that issue's **Build** list says. Don't start the next issue or change unrelated files.
- Each issue gets its own branch, created from an up-to-date `main` after the previous PR is merged. Name it `issue-<number>-<short-name>`, e.g. `issue-4-builtin-theme-catalogue`.
- Write tests for what you add. Then run `uv run pytest` and `uv run ruff check .`, fix any failures, and stop.
- Commit on the issue branch with the issue number in the message, e.g. `Built-in theme catalogue (#4)`.
- Ask before pushing the branch and before opening the PR. The PR targets `main` and its body starts with `Closes #<number>`.
- Finish with: the files you changed and why, and how to see it working.
- If anything isn't covered by the issue (a dependency, a version, an approach, extra files), ask first. Don't decide.

## Commands

```bash
uv run pytest                                  # tests (SQLite)
DATABASE_URL=postgres://... uv run pytest      # tests on Postgres
uv run ruff check .                            # lint
uv run python demo/manage.py tailwind runserver   # demo site at http://localhost:8000/
uv run django-admin makemigrations capy_theme --settings=tests.settings --pythonpath=.
```

## Rules that keep the module pluggable

- The installed package is only `src/capy_theme/`. `demo/` is development-only and never ships.
- Never import from a project or another module. Link to users with `settings.AUTH_USER_MODEL`.
- Templates go in `src/capy_theme/templates/capy_theme/` and static files in `src/capy_theme/static/capy_theme/`.
- Code lives in its section (`themes/`, `colors/`, `css/`, `fonts/`, `images/`, `editor/`, `artifacts/`, `admin/`), one job per file, and every Python file stays under 200 lines. Split a file before it grows past that.
- Project-configurable settings use the `CAPY_THEME_` prefix and have a sensible default.
- capy-theme handles every aspect of the theme but only applies it to the page's own look. Anything else (email, web app manifests, link-preview tags, an app shell) gets theme artifacts from `capy_theme.artifacts.get_artifacts()`, `{% theme_artifacts %}` or the JSON API; capy-theme doesn't do those jobs itself.

## Demo site accounts

- You may create a demo admin account in `demo/db.sqlite3` (git-ignored) when you need one to build or check something. Tell Sean its username and password.
- Delete every account you create before the project is finished, at the latest before the v1.0.0 release (issue 8.6), and tell Sean when it's done.
