# src/capy_theme/themes/active.py

**What it is:** decides **which theme a request gets**, and caches the answer so a normal page load doesn't query the database.

**The rules, in order:**

1. A visitor's own choice (the `capy_theme_choice` cookie), if that theme is offered and published and `CAPY_THEME_VISITOR_THEMES` is on.
2. A running scheduled assignment for this domain, then this domain's default.
3. A running scheduled assignment for every site, then the every-site default. If schedules overlap, the most recently started wins.

**Main functions:**

- `get_active_theme(request)`: the theme to show, with its live revision.
- `get_site_theme(request)`: the same but ignoring the visitor's choice.
- `offered_themes()`
- `activate(theme, site)`: the Activate action; the theme must be published.
- `theme_at(when, site)`: uncached, for "See it as a visitor" on a date.
- `scheduled_assignments(site)`

**Caching:**

- The state per domain is cached for `CAPY_THEME_CACHE_SECONDS`, but expires early at the next schedule start or end, so schedules switch on time.
- `clear_cache()` changes a "generation" key, which drops every domain's cache at once. `signals.py` calls it on every change.
