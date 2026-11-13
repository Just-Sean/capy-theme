# src/capy_theme/static/capy_theme/admin/color_input.js

**What it is:** a 13-line script that links each admin color text box to the color picker beside it.

- Picking a color writes its hex value into the box.
- Typing a hex value moves the picker. Other formats (rgb, oklch, names) are converted when the form is saved.

It's loaded by `ColorWidget`'s form media.
