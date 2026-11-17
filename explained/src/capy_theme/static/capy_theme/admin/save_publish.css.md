# src/capy_theme/static/capy_theme/admin/save_publish.css

**What it is:** the look of the theme page's **Save and publish** area (`save_publish.html`) and the theme list's row buttons (#273).

- The status line's items sit in a row and wrap; long theme names break rather than overflow.
- The note box sits above the buttons and is up to 32 rem wide.
- The buttons are stacked, each with its description beside it, and sized like Django's own save buttons. On screens 640 px wide or less they fill the width.
- The Delete or Close link sits just below the area.
- On the theme list, the **Publish**, **Publish and activate** and **Activate** buttons wrap and have gaps. On touch screens they're taller (2.75 rem), so they're easier to tap.

It's loaded by `theme_change_form.html` and `theme_change_list.html`.
