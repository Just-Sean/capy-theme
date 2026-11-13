# src/capy_theme/colors/fields.py

**What it is:** the admin form's color input.

- **`ColorWidget`:** a text box plus the browser's color picker beside it. Its template is `widgets/color.html`; `admin/color_input.js` keeps the two in step. The picker shows the current value, or the base color when blank.
- **`ColorField`:** accepts any color format and cleans it to OKLCH text. A blank value means "use the base theme's color". Anything that isn't a color gets a clear error with examples.
