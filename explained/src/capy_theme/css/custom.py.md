# src/capy_theme/css/custom.py

**What it is:** custom CSS, the escape hatch for anything the settings don't cover. It's stored in the theme's settings as `{"css": ..., "enabled": ...}`, so it's drafted and published like everything else. At most 100,000 characters.

- **`custom_css(snapshot)`:** the revision's CSS if it's switched on (and `CAPY_THEME_CUSTOM_CSS` allows it), else "".
- **`custom_css_url(revision)`:** its file's URL, or None.
- **`can_edit_custom_css(user)`:** the project allows it and the user has `edit_custom_css`.
- **`summary(settings)`:** "on, 120 characters". Used where the content mustn't be shown, like revision comparisons.
- **`without_custom_css(settings)`:** the settings minus the CSS, for the editor and others who mustn't see it.
