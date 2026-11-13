# src/capy_theme/admin/schedule.py

**What it is:** **Theme schedule**, the admin for scheduled themes (`ScheduledTheme`).

- Pick a published theme, a start and/or end date, and optionally a domain.
- The list shows each schedule's site and status: **Upcoming**, **Running** or **Finished**.
- Needs `publish_theme` (`PublishPermissionMixin`).
