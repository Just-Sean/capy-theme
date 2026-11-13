# CLAUDE.md

**What it is:** project instructions Claude Code reads at the start of every session here. They add to your global rules in `~/.claude/CLAUDE.md`.

**What it says:**

- The build plan is in `docs/PLAN.md`, one GitHub issue per step.
- Work one issue at a time, each on its own `issue-<number>-<name>` branch, with tests. Run `uv run pytest` and `uv run ruff check .`, ask before pushing or opening a PR, and use `Closes #N` in the PR.
- The common commands.
- **Rules that keep the module pluggable:**
  - only `src/capy_theme/` ships
  - never import from a project
  - templates and static files go in their `capy_theme/` folders
  - each section in its own folder, one job per file
  - files under about 300 lines
  - data in JSON, not Python
  - settings use the `CAPY_THEME_` prefix
  - other jobs (email, manifests, link previews) get theme artifacts instead of capy-theme doing them
- **Demo accounts:** Claude may create one but must delete it before v1.0.0.
