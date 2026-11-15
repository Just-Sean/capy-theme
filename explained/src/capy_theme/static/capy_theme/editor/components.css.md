# src/capy_theme/static/capy_theme/editor/components.css

**What it is:** **built, don't edit by hand.** About 115 KB of minified daisyUI 5.7.50 plus Tailwind 4.3.4. It holds only the classes used by:

- the Components view's templates
- the live edit page's templates (`live_edit.html`, `live_edit_components.html`)
- the mode toggle and theme picker that the live edit page shows

**Made by:** `scripts/build_components_css.py`. Rebuild it after changing any of those templates or updating daisyUI. Otherwise new classes stay unstyled.

**Why it ships:** it's committed and shipped, so the Components view and the live edit page work in any project, even one without Tailwind or daisyUI.

**Where it's used:**

- inside the Components view's iframe
- on capy-theme's own live edit page (`/theme/live-edit/`)

It never touches a project's own pages.
