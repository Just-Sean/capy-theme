# src/capy_theme/css/backgrounds.py

**What it is:** the two optional background images, the **login background** and the **page pattern**.

- **`css_variables(snapshot, scheme)`:** `--capy-bg-login` / `--capy-bg-pattern` as `url("...")` for each mode. Dark mode falls back to the light image. The URL is escaped for CSS.
- **`helper_css()`:** the classes `.capy-bg-login` (covers the element, centered) and `.capy-bg-pattern` (repeats), in `@layer base` so a project's classes win.
- **`template_values(snapshot)`:** the light URLs for templates (`theme.background_login_url`, ...).

They show only where a project's templates use them. The demo's `<body>` uses `capy-bg-pattern`.
