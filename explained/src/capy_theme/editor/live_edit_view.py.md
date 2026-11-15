# src/capy_theme/editor/live_edit_view.py

**The live edit page** at `/theme/live-edit/` (issue #229). It's capy-theme's own page for building a theme: the header and every daisyUI component, with the live editor open on it. It looks and works the same in every project.

**Who can open it:** staff who can change themes (`can_edit`).

- Logged out: redirected to the admin login, coming back afterwards.
- Anyone else: `PermissionDenied`, so the project's 403 page.

**Which theme:** `?edit=<id>` (read by `access.requested_theme_id`, ASCII digits only).

- Without a readable id, the view redirects to the active theme, or else the first theme.
- With no themes, the page links to the admin to add one.
- For an id that doesn't exist, the page says so.

**Other rules:**

- **Self-contained:** it passes `theme` (the published theme, for the header), `request` and `editing` (the theme being edited, for the title) itself. So the project doesn't need capy-theme's or Django's request context processor.
- **`X-Frame-Options: DENY`** comes from the view itself, so no site can frame the editor and trick a click on Save or Publish, even in a project without the clickjacking middleware.
- **Only GET, never cached.** It needs Django's admin at its usual `admin` namespace.
- **Linked from the admin:** the admin's **Edit live** (`admin/theme_admin.py`) links here.
