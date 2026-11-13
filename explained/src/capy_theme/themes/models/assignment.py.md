# src/capy_theme/themes/models/assignment.py

**What it is:** `ThemeAssignment`, which records **which theme is live**, plus two admin-only views of it.

**An assignment has:**

- a theme
- a `site`: a domain, or blank for every site
- optional `starts_at` / `ends_at` dates

**Kinds:**

- **Default:** no dates. Only one per site (a database constraint). Set by `active.activate()`, the admin's Activate action.
- **Scheduled:** has dates, and wins while running (start included, end not). Used for holiday themes, for example.
- **Per site:** an assignment with a domain wins over the every-site ones on that domain.

**`clean()` checks:**

- the domain is just a domain (no `https://`, path or port), and it's lower-cased
- the end is after the start
- the theme is published

**Proxy models** (same table, different admin pages):

- `ScheduledTheme` is "Theme schedule".
- `SiteTheme` is "Site themes".
