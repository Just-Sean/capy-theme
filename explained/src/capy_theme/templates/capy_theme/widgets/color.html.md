# src/capy_theme/templates/capy_theme/widgets/color.html

**What it is:** the admin's color field: Django's normal text input plus the browser's `<input type="color">` picker beside it, linked by `data-capy-color-for`. `static/capy_theme/admin/color_input.js` keeps them in step. The picker has an `aria-label`.

It uses an inline `style` attribute for the picker's size, which a strict CSP would block (#214).
