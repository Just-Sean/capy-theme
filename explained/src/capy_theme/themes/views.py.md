# src/capy_theme/themes/views.py

**What it is:** the two public URLs visitors use. Both work without JavaScript.

- **`set_mode`** (`/theme/mode/<light|dark|auto>/`): stores the visitor's mode in a cookie (only if the theme allows switching), then goes back to the page.
- **`choose_theme`** (`/theme/choose/<slug>/`): stores an **offered** theme's slug in a cookie, or `default` clears it, then goes back. Themes that aren't offered are ignored, so visitors can't force a theme.

**Security details:**

- **`_safe_next`:** only sends visitors back to pages on this site, which prevents open redirects.
- **Cookie values:** taken from the allowed list, never copied from the URL (this satisfies CodeQL's cookie-injection check).
- **Cookie flags:** `SameSite=Lax`. The theme cookie is HttpOnly; the mode cookie isn't, because the head script reads it.
