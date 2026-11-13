# README.md

**What it is:** the main documentation, and the page GitHub shows first. About 580 lines.

**Sections:**

- **What it does:** the feature overview.
- **Add it to a project:** installing, settings, URLs and the template tags. Includes **Tailwind and daisyUI for a new project**.
- **Backing up**, **Logging**, **Settings:** running it in production. Settings lists every `CAPY_THEME_*` setting.
- **Develop it:** working on capy-theme itself:
  - setup and the pre-commit checks
  - pip-audit and coverage
  - the GitHub Actions checks
- **Commands:** every command you'd run by hand.
- **Documentation:** links to the `docs/` files.
- **Upgrading**, **Build the package**, **Release a version:** maintenance.
- **License**, **Rules that keep it pluggable**, **Code layout:** the folder structure, which serves as the architecture overview.

**Rule:** every command you need goes in the README, in the same PR as the change that adds it.

**Known stale bit:** the intro still mentions "v0.7".
