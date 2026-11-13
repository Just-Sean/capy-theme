# demo/demo_site/settings.py

**What it is:** the demo's Django settings. It shows what a project needs to use capy-theme.

**What matters for capy-theme:**

- `"capy_theme"` in `INSTALLED_APPS`.
- `capy_theme.context_processors.theme` in the template context processors. This makes `{{ theme }}` available in every template: site name, tagline, logo URL, email colors, and so on.
- `MEDIA_URL` / `MEDIA_ROOT` (`demo/media/`), where uploaded images and fonts are stored.

**The rest:**

- **Dev-only basics:**
  - `SECRET_KEY = "demo-only-not-secret"` (ruff is told to allow it)
  - `DEBUG = True`
  - only localhost in `ALLOWED_HOSTS`
- **Database:** SQLite in `demo/db.sqlite3` by default, or Postgres if `DATABASE_URL` is set (read with `dj-database-url`).
- **`django_tailwind_cli`:** demo only. It downloads the Tailwind program (version `TAILWIND_CLI_VERSION`, kept in step with CI's checksum) and builds `tailwind/source.css` into `static/css/tailwind.css`.
- **Standard Django parts:** admin, auth, sessions, messages and their middleware (including CSRF and clickjacking protection), UTC time zone, English.

There's no Content Security Policy set up here. Strict CSP support is tracked as issue #214.
