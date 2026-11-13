# src/capy_theme/editor/visitors.py

**What it is:** **See it as a visitor**.

- **`visitor_summary(request)`:** what's set up for visitors on this domain: the live theme, its default mode and whether visitors can switch, the offered themes, and running and upcoming schedules with dates.
- **`visitor_view(theme_slug, day, request)`:** the **published** CSS a visitor would get, from one of:
  - the site's theme now
  - an offered theme (as a visitor's own choice would show it)
  - the site's theme at noon on a given date, including schedules, to check one before it starts

It uses the same rules as the live site and writes nothing.
