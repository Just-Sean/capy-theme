# capy-theme (the project root)

**What it is:** a reusable Django app, `capy_theme`, that themes any Django project using daisyUI 5. It handles a site's colors, shape, fonts, type scale, logos, icons, background images, light/dark mode and custom CSS. Changes are made as drafts, previewed live, then published as numbered revisions.

**How the project is laid out:**

| Folder / file | Purpose |
| --- | --- |
| `src/capy_theme/` | **The app itself.** Only this folder is installed into other projects. |
| `tests/` | The automated tests (pytest), mirroring `src/capy_theme/`. |
| `demo/` | A small Django site for trying the app by hand. Development only; never shipped. |
| `docs/` | Longer documentation: one file per feature area, plus the plan and the decisions log. |
| `scripts/` | Helper scripts that regenerate data files (built-in themes, bundled fonts, the Components view's CSS). |
| `.github/` | GitHub Actions: the checks run on every PR. |
| `.claude/` | Local Claude Code settings (not committed). |
| `explained/` | This folder: a file-by-file explanation of the project. |
| `pyproject.toml`, `uv.lock`, `.python-version` | The Python project: dependencies, tool settings, exact locked versions, Python version. |
| `.pre-commit-config.yaml` | Checks that run on every `git commit` (secrets and lint). |
| `README.md`, `CHANGELOG.md`, `CLAUDE.md` | Main docs, release notes, and the instructions Claude follows here. |
| `LICENSE`, `THIRD_PARTY_NOTICES.md` | MIT license, and the licenses of included third-party work (daisyUI, fonts...). |

**Not in git (made by tools, safe to delete; they come back):**

- `.venv/`: the project's Python environment, made by `uv sync`.
- `.pytest_cache/`, `.ruff_cache/`: caches pytest and ruff keep to run faster.
- `.coverage`: the last test-coverage result (`uv run pytest --cov`).
- `.git/`: git's own history database (not a build artifact, but never edited by hand).

**How the pieces connect:** a project installs `capy_theme`, adds it to `INSTALLED_APPS`, includes its URLs under `/theme/`, and puts its template tags (`{% theme_head %}` and friends) in its base template. Staff then edit themes in the admin or the live editor; visitors get the published theme's stylesheet.
