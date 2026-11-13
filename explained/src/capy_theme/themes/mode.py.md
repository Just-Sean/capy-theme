# src/capy_theme/themes/mode.py

**What it is:** light, dark and auto.

- **`mode_settings(revision)`:** the theme's default mode and whether visitors can switch.
- **`current_mode(request, revision)`:** the visitor's cookie choice (`capy_theme_mode`) if switching is allowed, else the default.
- **`html_theme_value(mode)`:** `capy-light` / `capy-dark` for `<html data-theme=...>`, or nothing for auto.
- **`head_script(revision)`:** a tiny inline script `{% theme_head %}` outputs. It:
  - applies the mode from the cookie **before the page draws** (no flash, and right even on cached pages)
  - makes the toggle buttons switch instantly without reloading, marking the current one with `aria-current`
- **`theme_color_meta(revision, mode)`:** `<meta name="theme-color">` tags so phones color their address bar to match the page background: one per mode, or one if a mode is forced.
- The cookie lasts a year.
