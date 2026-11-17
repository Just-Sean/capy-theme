# src/capy_theme/static/capy_theme/admin/confirm.js

**What it is:** a small script that asks before a button that changes what visitors see (publish, activate) goes ahead (#273).

- Any button with a `data-capy-confirm` attribute shows that text as a question when clicked. **Cancel** stops it.
- It listens on the whole page, so it covers the theme page's publishing buttons and the theme list's row buttons.
- Without JavaScript the buttons just work, without the question.
- No inline script, so it works with a strict Content Security Policy.

Loaded by `templates/capy_theme/admin/theme_change_form.html` and `theme_change_list.html`.
