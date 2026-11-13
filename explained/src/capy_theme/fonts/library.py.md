# src/capy_theme/fonts/library.py

**What it is:** fonts as the rest of the app uses them.

- **`ROLES`:** body, heading, mono, display, with labels.
- **`DEFAULT_FALLBACK`:** sensible fallback stacks per role. `SYSTEM_STACKS` is loaded from `system_stacks.json`.
- **`resolve(font)` / `snapshot_fonts(settings)`:** the chosen fonts as plain data (family, source, fallback, stylesheet, file URLs) for a revision's snapshot.
- **`stack(role, font)`:** the CSS `font-family` value, e.g. `"Inter", ui-sans-serif, system-ui, sans-serif`. A system stack is just its own list.
- **`preview_stack()` / `preview_faces()`:** for showing a sample of a font in the admin list and the editor.
- **`external_stylesheets(fonts)`:** the external stylesheet URLs `{% theme_head %}` must link.
- **`preload_urls(fonts)`:** the body and heading fonts' regular files, preloaded in `<head>` so text shows in the right font sooner.
