# src/capy_theme/admin/schedule.py

**What it is:** **Theme schedule**, the admin for scheduled themes (`ScheduledTheme`).

- Pick a published theme, a start and/or end date, and optionally a domain.
- The list shows each schedule's site and status: **Upcoming**, **Running** or **Finished**.
- Without dates it's refused: the site's default theme is set with **Activate** on the theme list or the theme's page instead.
- Needs `publish_theme` (`PublishPermissionMixin`).
