# src/capy_theme/editor/live_edit_view.py

**The live edit page** at `/theme/live-edit/` (issue #229). It's capy-theme's own page for building a theme: the header and every daisyUI component, with the live editor open on it. It looks and works the same in every project.

- **Who:** staff who can change themes (`can_edit`).
  - Logged out: redirected to the admin login, coming back afterwards.
  - Anyone else: 403.
- **Which theme:** `?edit=<id>`. Without it, the view redirects to the active theme, or else the first theme. With no themes at all, the page shows a link to add one.
- **Self-contained:** it passes `theme` (from the context processor's function) and `request` itself, so the project doesn't need capy-theme's or Django's request context processor.
- **Only GET, never cached.**
- The admin's **Edit live** (`admin/theme_admin.py`) links here.
